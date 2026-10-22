from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.health import HealthService


@pytest.mark.asyncio
async def test_db_ready_success():
    """Проверка успешного коннекта к БД."""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    service = HealthService(pool=mock_pool, redis=AsyncMock())

    assert await service.db_ready() is True
    mock_conn.fetch.assert_called_once_with("SELECT 1;")


@pytest.mark.asyncio
async def test_db_ready_failure():
    """Проверка обработки ошибки при падении БД."""
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.side_effect = Exception("DB Connection Refused")

    service = HealthService(pool=mock_pool, redis=AsyncMock())

    assert await service.db_ready() is False


@pytest.mark.asyncio
async def test_cache_ready_success():
    """Проверка успешного пинга Redis."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    service = HealthService(pool=MagicMock(), redis=mock_redis)

    assert await service.cache_ready() is True
    mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_cache_ready_failure():
    """Проверка обработки ConnectionError в Redis."""
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = ConnectionError("Redis down")

    service = HealthService(pool=MagicMock(), redis=mock_redis)

    assert await service.cache_ready() is False
