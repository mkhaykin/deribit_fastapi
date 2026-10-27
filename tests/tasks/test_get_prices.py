import json
import logging
from decimal import Decimal

import pytest
from aiohttp.web_request import BaseRequest

from tasks.fetch_data import QueryTicket, get_prices


@pytest.fixture
def fetch_data():
    def _func(index_price: str = "1.234") -> str:
        return json.dumps(
            {
                "usIn": 1,
                "usOut": 2,
                "usDiff": 3,
                "result": {
                    "estimated_delivery_price": index_price,
                    "index_price": index_price,
                },
            }
        )

    return _func


@pytest.mark.asyncio
async def test_get_prices_full_success(fetch_data, aresponses, caplog):
    """полное получение всех данных"""
    test_logger = logging.getLogger("test_logger")
    caplog.set_level(logging.WARNING, logger="test_logger")
    prices = {
        "btc_usd": "65000.4",
        "eth_usd": "3500.3",
    }

    async def response_func(request: BaseRequest) -> aresponses.Response:
        index_name = request.query["index_name"]
        return aresponses.Response(
            text=fetch_data(index_price=prices[index_name]), status=200, content_type="application/json"
        )

    aresponses.add("fakeapi.com", "/public/get_index_price", "GET", response=response_func, repeat=2)
    results, exc = await get_prices(
        [
            QueryTicket(
                index_name="btc_usd",
                url="http://fakeapi.com/public/get_index_price?index_name=btc_usd",
            ),
            QueryTicket(
                index_name="eth_usd",
                url="http://fakeapi.com/public/get_index_price?index_name=eth_usd",
            ),
        ],
        logger=test_logger,
    )

    assert len(results) == 2
    assert {r.index_name for r in results} == {"btc_usd", "eth_usd"}
    for r in results:
        assert r.result.estimated_delivery_price == Decimal(prices[r.index_name])

    # WARNING быть не должно, так как набор полный
    assert "Incomplete price set" not in caplog.text


@pytest.mark.parametrize(
    [
        "broken_query",
    ],
    [
        ("btc_usd",),
        ("eth_usd",),
    ],
)
@pytest.mark.asyncio
async def test_get_prices_partial_success(
    fetch_data,
    aresponses,
    caplog,
    broken_query: str,
):
    """частичное получение данных (падаем на эфире)"""
    test_logger = logging.getLogger("test_logger")
    caplog.set_level(logging.WARNING, logger="test_logger")

    prices = {
        "btc_usd": "65000.4",
        "eth_usd": "3500.3",
    }

    async def response_func(request: BaseRequest) -> aresponses.Response:
        index_name = request.query["index_name"]
        if index_name == broken_query:
            return aresponses.Response(status=500)

        return aresponses.Response(
            text=fetch_data(index_price=prices[index_name]), status=200, content_type="application/json"
        )

    aresponses.add("fakeapi.com", "/public/get_index_price", "GET", response=response_func, repeat=2)

    results, exc = await get_prices(
        [
            QueryTicket(
                index_name="btc_usd",
                url="http://fakeapi.com/public/get_index_price?index_name=btc_usd",
            ),
            QueryTicket(
                index_name="eth_usd",
                url="http://fakeapi.com/public/get_index_price?index_name=eth_usd",
            ),
        ],
        logger=test_logger,
    )

    assert len(results) == 1

    result = results[0]
    assert result.index_name != broken_query
    assert result.result.estimated_delivery_price == Decimal(prices[result.index_name])

    # сработал варнинг о неполном наборе данных
    assert f"Incomplete price set; missing: {broken_query}" in caplog.text


@pytest.mark.asyncio
async def test_get_prices_full_failure(aresponses, caplog):
    """Сценарий 3: Полное отсутствие данных (оба запроса упали)"""
    test_logger = logging.getLogger("test_logger")
    caplog.set_level(logging.WARNING, logger="test_logger")

    aresponses.add(
        "fakeapi.com", "/public/get_index_price?index_name=btc_usd", "GET", aresponses.Response(status=500)
    )
    aresponses.add(
        "fakeapi.com", "/public/get_index_price?index_name=eth_usd", "GET", aresponses.Response(status=500)
    )

    results, exc = await get_prices(
        [
            QueryTicket(
                index_name="btc_usd",
                url="http://fakeapi.com/public/get_index_price?index_name=btc_usd",
            ),
            QueryTicket(
                index_name="eth_usd",
                url="http://fakeapi.com/public/get_index_price?index_name=eth_usd",
            ),
        ],
        logger=test_logger,
    )

    assert len(results) == 0

    # оба отсутствующих тикера ...
    assert "Incomplete price set; missing: btc_usd, eth_usd" in caplog.text
