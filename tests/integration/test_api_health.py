from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from httpx2 import AsyncClient


@pytest.fixture
def broken_db_pool(api_app):
    """временно ломает пул БД, conn.fetch выбрасывает ошибку"""
    old_pool = api_app.state.pool

    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = Exception("DB Connection Refused")

    mock_acquire_context = MagicMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = mock_acquire_context
    api_app.state.pool = mock_pool

    yield api_app

    api_app.state.pool = old_pool


@pytest.mark.asyncio
async def test_healthz_endpoint(api_client: AsyncClient):
    """тут всегда ок"""
    response = await api_client.get("/healthz")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readyz_endpoint_success(api_client: AsyncClient):
    """всё поднято, все ок"""
    response = await api_client.get("/readyz")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readyz_endpoint_db_down(api_client: AsyncClient, broken_db_pool):
    """readyz при «упавшем» postgres"""
    response = await api_client.get("/readyz")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "status": "unready",
        "db": "down",
        "cache": "up",
    }


@pytest.mark.asyncio
async def test_readyz_endpoint_redis_down(api_client: AsyncClient, api_app):
    """readyz при «упавшем» redis."""
    # ломаем ping
    api_app.state.redis.ping = AsyncMock(side_effect=ConnectionError("Redis connection lost"))

    response = await api_client.get("/readyz")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "degraded",
        "db": "up",
        "cache": "down",
    }
