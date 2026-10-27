import asyncio
import logging

import aiohttp
import pytest
from pydantic import BaseModel

from tasks.price_collector.fetch_data import _fetch_index


class DummyModel(BaseModel):
    index_name: str
    price: float


@pytest.mark.asyncio
async def test_fetch_url_success_with_mock(aresponses):
    url = "http://fakeapi.com/public/get_index_price"
    index_name = "btc_usd"

    aresponses.add(
        aresponses.ANY,
        aresponses.ANY,
        "GET",
        aresponses.Response(
            text='{"index_name": "btc_usd", "price": 65000.0}', status=200, content_type="application/json"
        ),
    )

    async with aiohttp.ClientSession() as session:
        result = await _fetch_index(session, url, index_name, DummyModel)

        assert isinstance(result, DummyModel)
        assert result.price == 65000.0
        assert result.index_name == "btc_usd"


@pytest.mark.asyncio
async def test_fetch_url_network_error_with_mock(aresponses, caplog):
    url = "http://fakeapi.com/public/get_index_price"

    aresponses.add(aresponses.ANY, aresponses.ANY, "GET", aresponses.Response(status=500))

    async with aiohttp.ClientSession() as session:
        # Проверяем, что функция логирует и прокидывает ClientResponseError наверх
        with pytest.raises(aiohttp.ClientResponseError):
            await _fetch_index(session, url, "btc_usd", DummyModel, logger=logging.getLogger(__name__))
        assert "Response error fetching" in caplog.text


@pytest.mark.asyncio
async def test_fetch_url_timeout_error(aresponses):
    url = "http://fakeapi.com/public/get_index_price"

    async def raise_timeout(*args, **kwargs):
        await asyncio.sleep(1)
        raise RuntimeError("Connection timed out")

    aresponses.add(aresponses.ANY, aresponses.ANY, "GET", raise_timeout)

    short_timeout = aiohttp.ClientTimeout(total=0.01)
    async with aiohttp.ClientSession(timeout=short_timeout) as session:
        with pytest.raises(asyncio.TimeoutError):
            await _fetch_index(session, url, "btc_usd", DummyModel)
