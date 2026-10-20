from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    api_keys,
    auth,
    artifacts,
    deployments,
    environments,
    incidents,
    monitors,
    notifications,
    projects,
    runs,
    workspaces,
)
from app.core.rate_limit import api_rate_limit

api_router = APIRouter(dependencies=[Depends(api_rate_limit)])

api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(projects.router)
api_router.include_router(environments.router)
api_router.include_router(monitors.router)
api_router.include_router(runs.router)
api_router.include_router(deployments.router)
api_router.include_router(incidents.router)
api_router.include_router(notifications.router)
api_router.include_router(api_keys.router)
api_router.include_router(artifacts.router)
