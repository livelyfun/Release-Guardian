import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.errors import install_error_handlers
from app.core.metrics import API_LATENCY, API_REQUESTS, render_metrics
from app.core.observability import configure_logging, request_id_var
from app.core.production import validate_production_settings

logger = logging.getLogger("release_guardian.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != "production":
        import app.models  # noqa: F401  (register metadata)

        Base.metadata.create_all(bind=engine)
    logger.info("api_started", extra={"environment": settings.environment})
    yield
    logger.info("api_stopped")


def create_app() -> FastAPI:
    validate_production_settings(settings)
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Website reliability, synthetic monitoring, and release verification API.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def observe_request(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - started
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            API_REQUESTS.inc(method=request.method, route=route_path, status=str(status_code))
            API_LATENCY.observe(elapsed, method=request.method, route=route_path)
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            request_id_var.reset(token)

    install_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": "0.1.0",
            "environment": settings.environment,
            "worker_mode": settings.worker_mode,
        }

    @app.get("/ready", tags=["meta"])
    def ready() -> Response:
        checks: dict[str, str] = {}
        ok = True

        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - readiness must never raise
            checks["database"] = f"error: {exc}"
            ok = False

        if settings.worker_mode == "celery" and settings.readiness_check_redis:
            try:
                import redis

                client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
                client.ping()
                checks["redis"] = "ok"
            except Exception as exc:  # noqa: BLE001
                checks["redis"] = f"error: {exc}"
                ok = False

        body = {"status": "ready" if ok else "not_ready", "checks": checks}
        return Response(
            content=json.dumps(body),
            status_code=200 if ok else 503,
            media_type="application/json",
        )

    @app.get("/metrics", tags=["meta"], include_in_schema=False)
    def metrics() -> PlainTextResponse:
        if not settings.metrics_enabled:
            return PlainTextResponse("metrics disabled\n", status_code=404)
        return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
