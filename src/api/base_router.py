from fastapi import APIRouter, Response, status

router = APIRouter()


@router.get("/favicon.ico", include_in_schema=False)
async def disable_favicon() -> Response:
    return Response(status_code=204)


@router.get("/")
async def hello() -> dict:
    return {"msg": "Hello World"}


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health() -> dict:
    return {"status": "alive"}


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def ready(response: Response) -> dict:
    is_pg_ok = True
    is_redis_ok = True
    # TODO проверить статус фактически

    if not is_pg_ok or not is_redis_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "db": "up" if is_pg_ok else "down",
            "cache": "up" if is_redis_ok else "down",
        }

    return {"status": "ready"}
