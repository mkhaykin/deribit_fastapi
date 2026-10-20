from datetime import datetime, timezone
from decimal import Decimal

import asyncpg
import pytest
from fastapi import FastAPI
from httpx2 import AsyncClient


async def insert_price(
    app: FastAPI,
    ticker: str,
    price: str,
    timestamp: int,
) -> None:
    pool: asyncpg.Pool = app.state.pool

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO index_prices (ticker, price, timestamp)
            VALUES ($1, $2, $3)
            """,
            ticker,
            Decimal(price),
            timestamp,
        )


def unix_timestamp(year: int, month: int, day: int) -> int:
    return int(
        datetime(
            year,
            month,
            day,
            tzinfo=timezone.utc,
        ).timestamp()
    )


@pytest.mark.asyncio
async def test_health_endpoint(api_client: AsyncClient) -> None:
    response = await api_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_get_all_returns_prices(
    api_client: AsyncClient,
    api_app: FastAPI,
) -> None:
    await insert_price(
        api_app,
        "BTC",
        "100.25",
        unix_timestamp(2025, 1, 1),
    )
    await insert_price(
        api_app,
        "BTC",
        "200.50",
        unix_timestamp(2025, 1, 2),
    )
    await insert_price(
        api_app,
        "ETH",
        "300.75",
        unix_timestamp(2025, 1, 2),
    )

    response = await api_client.get(
        "/api/v1/all",
        params={"ticker": "BTC"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(item["ticker"] == "BTC" for item in data)
    assert [item["timestamp"] for item in data] == [
        unix_timestamp(2025, 1, 2),
        unix_timestamp(2025, 1, 1),
    ]


@pytest.mark.asyncio
async def test_get_all_returns_empty_list_for_unknown_ticker(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/api/v1/all",
        params={"ticker": "UNKNOWN"},
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_latest_returns_404_for_unknown_ticker(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/api/v1/latest",
        params={"ticker": "UNKNOWN"},
    )

    assert response.status_code == 404
    assert "No data found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_latest_returns_price(
    api_client: AsyncClient,
    api_app: FastAPI,
) -> None:
    await insert_price(
        api_app,
        "BTC",
        "123.456",
        unix_timestamp(2025, 1, 2),
    )

    response = await api_client.get(
        "/api/v1/latest",
        params={"ticker": "BTC"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "BTC"
    assert Decimal(data["price"]) == Decimal("123.456")


@pytest.mark.asyncio
async def test_latest_uses_cache_on_second_request(
    api_client: AsyncClient,
    api_app: FastAPI,
) -> None:
    timestamp = unix_timestamp(2025, 1, 2)

    await insert_price(api_app, "BTC", "100", timestamp)

    first = await api_client.get(
        "/api/v1/latest",
        params={"ticker": "BTC"},
    )
    assert first.status_code == 200
    assert Decimal(first.json()["price"]) == Decimal("100")

    # Меняем PostgreSQL напрямую, не трогая Redis.
    await insert_price(api_app, "BTC", "200", timestamp + 1)

    second = await api_client.get(
        "/api/v1/latest",
        params={"ticker": "BTC"},
    )

    assert second.status_code == 200
    assert Decimal(second.json()["price"]) == Decimal("100")


@pytest.mark.asyncio
async def test_filter_returns_prices_for_requested_utc_date(
    api_client: AsyncClient,
    api_app: FastAPI,
) -> None:
    jan_2 = unix_timestamp(2025, 1, 2)
    jan_3 = unix_timestamp(2025, 1, 3)

    await insert_price(api_app, "BTC", "100", jan_2 - 1)
    await insert_price(api_app, "BTC", "200", jan_2)
    await insert_price(api_app, "BTC", "300", jan_3 - 1)
    await insert_price(api_app, "BTC", "400", jan_3)

    response = await api_client.get(
        "/api/v1/filter",
        params={
            "ticker": "BTC",
            "date": "2025-01-02",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert [item["timestamp"] for item in data] == [
        jan_3 - 1,
        jan_2,
    ]


@pytest.mark.asyncio
async def test_filter_rejects_invalid_date(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/api/v1/filter",
        params={
            "ticker": "BTC",
            "date": "not-a-date",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_filter_returns_empty_list_when_no_prices_match(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/api/v1/filter",
        params={
            "ticker": "BTC",
            "date": "2025-01-02",
        },
    )

    assert response.status_code == 200
    assert response.json() == []
