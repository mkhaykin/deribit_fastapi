from decimal import Decimal

import pytest

from tasks.price_collector.fetch_data import FetchModel, FetchResultModel
from tasks.price_collector.main import fetch_prices
from tasks.price_collector.schemas import IndexRequestTask


class FetchModelFake(FetchModel):
    # чтобы лишнее не заполнять, тут не важно
    usIn: int = 1
    usOut: int = 1
    usDiff: int = 1


PATH_TO_GET_PRICES = "tasks.price_collector.main.get_prices"


# Фикстура для фейковых входных данных
@pytest.fixture
def fake_indexes() -> list[IndexRequestTask]:
    return [
        {"index_name": "btc_usd", "url": "http://fakeapi.com"},
        {"index_name": "eth_usd", "url": "http://fakeapi.com"},
    ]


@pytest.fixture
def mock_fetched_items():
    # почти настоящий объект, но убираем не значащие поля
    btc_item = FetchModelFake(
        index_name="btc_usd",
        result=FetchResultModel(index_price=Decimal("5000.0"), estimated_delivery_price=Decimal(5500.0)),
    )
    eth_item = FetchModelFake(
        index_name="eth_usd",
        result=FetchResultModel(index_price=Decimal("3000.0"), estimated_delivery_price=Decimal(3500.0)),
    )
    return [btc_item, eth_item]


def test_fetch_prices_success(mocker, fake_indexes, mock_fetched_items):
    # патчим get_prices, возвращаем готовое
    mocker.patch(PATH_TO_GET_PRICES, return_value=(mock_fetched_items, None))

    result = fetch_prices(fake_indexes)

    assert len(result) == 2
    assert set(item["ticker"] for item in result) == {
        mock_item.index_name for mock_item in mock_fetched_items
    }
    assert set(item["price"] for item in result) == {
        str(mock_item.result.index_price) for mock_item in mock_fetched_items
    }
    assert all(item["ts"] for item in result)


def test_fetch_prices_partial_success(mocker, fake_indexes):
    mock_item_btc = mocker.MagicMock()
    mock_item_btc.index_name = "btc_usd"
    mock_item_btc.result.index_price = 50000.0

    # Имитируем, что ошибка была, но один элемент всё же вернулся
    mocker.patch(PATH_TO_GET_PRICES, return_value=([mock_item_btc], RuntimeError("API Error")))

    # Функция НЕ должна упасть, так как items не пустой
    result = fetch_prices(fake_indexes)

    assert len(result) == 1
    assert result[0]["ticker"] == "btc_usd"


# 3. Тест полного провала (исключение должно проброситься)
def test_fetch_prices_total_failure(mocker, fake_indexes):
    # Items пустой, ошибка присутствует
    mocker.patch(PATH_TO_GET_PRICES, return_value=([], RuntimeError("Connection refused")))

    # Проверяем, что таска Celery выбросит это исключение для ретрая
    with pytest.raises(RuntimeError, match="Connection refused"):
        fetch_prices(fake_indexes)
