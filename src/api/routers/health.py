from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from ..helpers import get_health_service
from ..services.health import HealthService

router = APIRouter()


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health() -> dict:
    return {"status": "alive"}


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def ready(
    response: Response,
    service: Annotated[HealthService, Depends(get_health_service)],
) -> dict:
    is_pg_ok = await service.db_ready()
    is_redis_ok = await service.cache_ready()

    if not is_pg_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "db": "up" if is_pg_ok else "down",
            "cache": "up" if is_redis_ok else "down",
        }

    if not is_redis_ok:
        return {
            "status": "degraded",
            "db": "up",
            "cache": "up" if is_redis_ok else "down",
        }

    return {"status": "ready"}
