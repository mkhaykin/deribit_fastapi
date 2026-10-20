import json
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from api.cache import PriceCache
from api.schemas import IndexPriceResponse


@pytest.fixture
def redis_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def cache(redis_mock: AsyncMock) -> PriceCache:
    return PriceCache(redis_mock)


@pytest.fixture
def price() -> IndexPriceResponse:
    return IndexPriceResponse(
        id=1,
        ticker="BTC",
        price=Decimal("65000.123456"),
        timestamp=1_760_000_000,
    )


@pytest.mark.asyncio
async def test_get_latest_returns_none_on_cache_miss(
    cache: PriceCache,
    redis_mock: AsyncMock,
) -> None:
    redis_mock.get.return_value = None

    result = await cache.get_latest("BTC")

    assert result is None
    redis_mock.get.assert_awaited_once_with("price:latest:BTC")


@pytest.mark.asyncio
async def test_get_latest_deserializes_cached_value(
    cache: PriceCache,
    redis_mock: AsyncMock,
    price: IndexPriceResponse,
) -> None:
    redis_mock.get.return_value = price.model_dump_json()

    result = await cache.get_latest("BTC")

    assert result == price
    assert isinstance(result.price, Decimal)


@pytest.mark.asyncio
async def test_set_latest_saves_json_with_ttl(
    cache: PriceCache,
    redis_mock: AsyncMock,
    price: IndexPriceResponse,
) -> None:
    await cache.set_latest("BTC", price, ttl=45)

    redis_mock.set.assert_awaited_once()
    args, kwargs = redis_mock.set.await_args

    assert args[0] == "price:latest:BTC"
    assert json.loads(args[1]) == json.loads(price.model_dump_json())
    assert kwargs == {"ex": 45}


@pytest.mark.asyncio
async def test_set_latest_uses_default_ttl(
    cache: PriceCache,
    redis_mock: AsyncMock,
    price: IndexPriceResponse,
) -> None:
    await cache.set_latest("BTC", price)

    _, kwargs = redis_mock.set.await_args
    assert kwargs == {"ex": 30}


@pytest.mark.asyncio
async def test_get_latest_rejects_invalid_cached_json(
    cache: PriceCache,
    redis_mock: AsyncMock,
) -> None:
    redis_mock.get.return_value = '{"id": "not-an-integer"}'

    with pytest.raises(Exception):
        await cache.get_latest("BTC")
