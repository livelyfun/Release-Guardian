import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
}


def error_body(status_code: int, message: str, details=None, request_id: str | None = None) -> dict:
    return {
        "error": {
            "code": ERROR_CODES.get(status_code, "error"),
            "message": message,
            "details": details,
            "request_id": request_id or uuid.uuid4().hex,
        }
    }


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        req_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.status_code, str(exc.detail), request_id=req_id),
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError):
        req_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        return JSONResponse(
            status_code=422,
            content=error_body(422, "Request validation failed", exc.errors(), req_id),
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(Exception)
    async def _generic_exc(request: Request, exc: Exception):
        req_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        return JSONResponse(
            status_code=500,
            content=error_body(500, "Internal server error", request_id=req_id),
            headers={"X-Request-ID": req_id},
        )
