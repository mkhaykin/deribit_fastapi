from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

import api.services.price as price_service_module
from api.schemas import IndexPriceResponse
from api.services.price import PriceService


@pytest.fixture
def price() -> IndexPriceResponse:
    return IndexPriceResponse(
        id=1,
        ticker="BTC",
        price=Decimal("65000.25"),
        timestamp=1_760_000_000,
    )


@pytest.fixture
def dependencies(monkeypatch):
    repository = AsyncMock()
    cache = AsyncMock()

    monkeypatch.setattr(
        price_service_module,
        "PriceRepository",
        lambda *args, **kwargs: repository,
    )
    monkeypatch.setattr(
        price_service_module,
        "LatestPriceCache",
        lambda *args, **kwargs: cache,
    )

    service = PriceService(
        pool=object(),
        redis=object(),
    )

    return service, repository, cache


@pytest.mark.asyncio
async def test_latest_returns_cached_price(
    dependencies,
    price: IndexPriceResponse,
) -> None:
    service, repository, cache = dependencies
    cache.get_latest.return_value = price

    result = await service.get_latest_by_ticker("BTC")

    assert result == price
    repository.get_latest_by_ticker.assert_not_awaited()
    cache.set_latest.assert_not_awaited()


@pytest.mark.asyncio
async def test_latest_reads_repository_on_cache_miss(
    dependencies,
    price: IndexPriceResponse,
) -> None:
    service, repository, cache = dependencies
    cache.get_latest.return_value = None
    repository.get_latest_by_ticker.return_value = price

    result = await service.get_latest_by_ticker("BTC")

    assert result == price
    repository.get_latest_by_ticker.assert_awaited_once_with("BTC")
    cache.set_latest.assert_awaited_once_with("BTC", price)


@pytest.mark.asyncio
async def test_latest_does_not_cache_missing_price(
    dependencies,
) -> None:
    service, repository, cache = dependencies
    cache.get_latest.return_value = None
    repository.get_latest_by_ticker.return_value = None

    result = await service.get_latest_by_ticker("UNKNOWN")

    assert result is None
    cache.set_latest.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_all_delegates_to_repository(
    dependencies,
    price: IndexPriceResponse,
) -> None:
    service, repository, _ = dependencies
    repository.get_all_by_ticker.return_value = [price]

    result = await service.get_all_by_ticker("BTC")

    assert result == [price]
    repository.get_all_by_ticker.assert_awaited_once_with("BTC", None, None, None)


@pytest.mark.asyncio
async def test_date_filter_uses_utc_day_boundaries(
    dependencies,
) -> None:
    service, repository, _ = dependencies
    repository.get_by_ticker_and_date.return_value = []

    await service.get_by_ticker_and_date(
        "BTC",
        date(2025, 1, 2),
    )

    repository.get_by_ticker_and_date.assert_awaited_once_with(
        "BTC",
        1735776000,  # 2025-01-02 00:00:00 UTC
        1735862400,  # 2025-01-03 00:00:00 UTC
        None,
        None,
    )
