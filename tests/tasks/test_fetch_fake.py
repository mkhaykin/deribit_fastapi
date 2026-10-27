import logging

import aiohttp
import pytest
from _pytest.logging import LogCaptureFixture
from pydantic import BaseModel, ValidationError

from tasks.fetch_data import _fetch_index


class DummyModel(BaseModel):
    index_name: str
    price: float


class FakeResponse:
    def __init__(self, text: str, status: int):
        self._text = text
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def raise_for_status(self):
        if self.status >= 400:
            request_info = aiohttp.RequestInfo(url="http://fake.url", method="GET", headers={})
            raise aiohttp.ClientResponseError(request_info=request_info, history=(), status=self.status)

    async def text(self) -> str:
        return self._text

    async def read(self) -> bytes:
        return self._text.encode()


class FakeClientSession:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status = status

    def get(self, url: str) -> FakeResponse:
        return FakeResponse(self.text, self.status)


@pytest.mark.asyncio
async def test_fetch_url_success_with_fake():
    fake_session = FakeClientSession(text='{"index_name": "eth_usd", "price": 3500.0}', status=200)

    result = await _fetch_index(fake_session, "", "eth_usd", DummyModel)

    assert result.price == 3500.0
    assert result.index_name == "eth_usd"


@pytest.mark.parametrize(
    ["wrong_text", "ticket"],
    [
        (
            "{'invalid': 'data'}",
            "eth_usd",
        ),
        (
            "{ it`s not a json",
            "eth_usd",
        ),
    ],
)
@pytest.mark.asyncio
async def test_fetch_url_validation_error_with_fake(
    caplog: LogCaptureFixture,
    wrong_text: str,
    ticket: str,
):
    # невалидный JSON, ломающий Pydantic схему
    fake_session = FakeClientSession(text=wrong_text, status=200)

    with pytest.raises(ValidationError):
        await _fetch_index(fake_session, "", ticket, DummyModel, logger=logging.getLogger(__name__))

    assert f"Validation failed for index '{ticket}'" in caplog.text
    assert wrong_text in caplog.text
