import asyncio
import logging

import aiohttp
import pytest
from pydantic import BaseModel

from config import config
from tasks.fetch_data import _fetch_url


class DummyModel(BaseModel):
    index_name: str
    price: float


@pytest.mark.asyncio
async def test_fetch_url_success_with_mock(aresponses):
    config.API_URL = "http://fakeapi.com"
    index_name = "btc_usd"

    aresponses.add(
        "fakeapi.com",
        "/public/get_index_price",
        "GET",
        aresponses.Response(
            text='{"index_name": "btc_usd", "price": 65000.0}', status=200, content_type="application/json"
        ),
    )

    async with aiohttp.ClientSession() as session:
        result = await _fetch_url(session, index_name, DummyModel)

        assert isinstance(result, DummyModel)
        assert result.price == 65000.0
        assert result.index_name == "btc_usd"


@pytest.mark.asyncio
async def test_fetch_url_network_error_with_mock(aresponses, caplog):
    config.API_URL = "http://fakeapi.com"

    aresponses.add("fakeapi.com", "/public/get_index_price", "GET", aresponses.Response(status=500))

    async with aiohttp.ClientSession() as session:
        # Проверяем, что функция логирует и прокидывает ClientResponseError наверх
        with pytest.raises(aiohttp.ClientResponseError):
            await _fetch_url(session, "btc_usd", DummyModel, logger=logging.getLogger(__name__))
        print(caplog.text)
        assert "Response error fetching" in caplog.text


@pytest.mark.asyncio
async def test_fetch_url_timeout_error(aresponses):
    config.API_URL = "http://fakeapi.com"

    async def raise_timeout(*args, **kwargs):
        await asyncio.sleep(1)
        raise asyncio.TimeoutError("Connection timed out")

    aresponses.add("fakeapi.com", "/public/get_index_price", "GET", raise_timeout)

    short_timeout = aiohttp.ClientTimeout(total=0.01)
    async with aiohttp.ClientSession(timeout=short_timeout) as session:
        with pytest.raises(asyncio.TimeoutError):
            await _fetch_url(session, "btc_usd", DummyModel)
