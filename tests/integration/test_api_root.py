import pytest
from fastapi import status
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_root_welcome_page(api_client: AsyncClient):
    """главная страница с документацией"""
    response = await api_client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]
    assert "Index Prices API" in response.text


@pytest.mark.asyncio
async def test_favicon_disabled(api_client: AsyncClient):
    """заглушка для favicon"""
    response = await api_client.get("/favicon.ico")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.text == ""
