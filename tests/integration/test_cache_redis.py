from decimal import Decimal

import pytest

from api.schemas import IndexPriceResponse
from api.services.cache import LatestPriceCache


@pytest.mark.asyncio
async def test_cache_round_trip(redis_client) -> None:
    cache = LatestPriceCache(redis_client)
    price = IndexPriceResponse(
        id=1,
        ticker="BTC",
        price=Decimal("123.456"),
        timestamp=1_760_000_000,
    )

    await cache.set_latest("BTC", price, ttl=60)
    result = await cache.get_latest("BTC")

    assert result == price


@pytest.mark.asyncio
async def test_cache_returns_none_for_missing_key(redis_client) -> None:
    cache = LatestPriceCache(redis_client)

    assert await cache.get_latest("UNKNOWN") is None


@pytest.mark.asyncio
async def test_cache_sets_expiration(redis_client) -> None:
    cache = LatestPriceCache(redis_client)
    price = IndexPriceResponse(
        id=1,
        ticker="BTC",
        price=Decimal("100"),
        timestamp=100,
    )

    await cache.set_latest("BTC", price, ttl=60)

    ttl = await redis_client.ttl("price:latest:BTC")

    assert 0 < ttl <= 60


@pytest.mark.asyncio
async def test_cache_key_isolated_by_ticker(redis_client) -> None:
    cache = LatestPriceCache(redis_client)

    btc = IndexPriceResponse(
        id=1,
        ticker="BTC",
        price=Decimal("100"),
        timestamp=100,
    )
    eth = IndexPriceResponse(
        id=2,
        ticker="ETH",
        price=Decimal("200"),
        timestamp=200,
    )

    await cache.set_latest("BTC", btc)
    await cache.set_latest("ETH", eth)

    assert await cache.get_latest("BTC") == btc
    assert await cache.get_latest("ETH") == eth
