from decimal import Decimal

import pytest
import pytest_asyncio

from api.repository import PriceRepository


@pytest_asyncio.fixture
async def repository(pg_pool):
    return PriceRepository(pg_pool)


@pytest_asyncio.fixture
async def seed_prices(pg_pool):
    async with pg_pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO index_prices (ticker, price, timestamp)
            VALUES ($1, $2, $3)
            """,
            [
                ("BTC", Decimal("100.10"), 100),
                ("BTC", Decimal("200.20"), 200),
                ("BTC", Decimal("300.30"), 300),
                ("ETH", Decimal("400.40"), 250),
            ],
        )


@pytest.mark.asyncio
async def test_get_all_returns_only_requested_ticker(
    repository,
    seed_prices,
) -> None:
    result = await repository.get_all_by_ticker("BTC")

    assert len(result) == 3
    assert all(item.ticker == "BTC" for item in result)


@pytest.mark.asyncio
async def test_get_all_orders_by_timestamp_desc(
    repository,
    seed_prices,
) -> None:
    result = await repository.get_all_by_ticker("BTC")

    assert [item.timestamp for item in result] == [300, 200, 100]


@pytest.mark.asyncio
async def test_get_all_returns_empty_list_for_unknown_ticker(
    repository,
) -> None:
    assert await repository.get_all_by_ticker("UNKNOWN") == []


@pytest.mark.asyncio
async def test_get_latest_returns_most_recent_price(
    repository,
    seed_prices,
) -> None:
    result = await repository.get_latest_by_ticker("BTC")

    assert result is not None
    assert result.timestamp == 300
    assert result.price == Decimal("300.30")


@pytest.mark.asyncio
async def test_get_latest_returns_none_for_unknown_ticker(
    repository,
) -> None:
    assert await repository.get_latest_by_ticker("UNKNOWN") is None


@pytest.mark.asyncio
async def test_date_filter_uses_half_open_interval(
    repository,
    pg_pool,
) -> None:
    async with pg_pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO index_prices (ticker, price, timestamp)
            VALUES ($1, $2, $3)
            """,
            [
                ("BTC", Decimal("10"), 100),
                ("BTC", Decimal("20"), 199),
                ("BTC", Decimal("30"), 200),
            ],
        )

    result = await repository.get_by_ticker_and_date(
        "BTC",
        100,
        200,
    )

    assert [item.timestamp for item in result] == [199, 100]
