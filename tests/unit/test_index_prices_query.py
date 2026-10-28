import re

import pytest

from api.repository import PriceRepository


@pytest.fixture
def normalize_sql():
    """Фикстура преобразует любые последовательности пробелов и переносов строк в один пробел,
    а также убирает пробелы по краям. Защищает тесты от хрупкости при форматировании."""

    def _normalize(sql: str) -> str:
        return re.sub(r"\s+", " ", sql).strip()

    return _normalize


def test_build_query_base_case(normalize_sql):
    """Тест базового сценария: только тикер, без пагинации и лимитов."""
    ticker = "AAPL"

    query, args = PriceRepository._build_query_for_all(ticker, None, None, None)

    expected_sql = """
        SELECT id, ticker, price, timestamp
        FROM index_prices
        WHERE ticker = $1
        ORDER BY timestamp DESC, id DESC
    """
    assert normalize_sql(query) == normalize_sql(expected_sql)
    assert args == ["AAPL"]


def test_build_query_with_limit(normalize_sql):
    """Тест сценария с лимитом, но без курсора."""
    ticker = "MSFT"
    limit = 10

    query, args = PriceRepository._build_query_for_all(ticker, None, None, limit)

    expected_sql = """
        SELECT id, ticker, price, timestamp
        FROM index_prices
        WHERE ticker = $1
        ORDER BY timestamp DESC, id DESC
        LIMIT $2
    """
    assert normalize_sql(query) == normalize_sql(expected_sql)
    assert args == ["MSFT", 10]


def test_build_query_with_cursor_and_limit(normalize_sql):
    """Тест полного сценария: тикер + курсор + лимит."""
    ticker = "TSLA"
    last_created_at = 1713541200
    last_id = 42
    limit = 50

    query, args = PriceRepository._build_query_for_all(ticker, last_created_at, last_id, limit)

    expected_sql = """
        SELECT id, ticker, price, timestamp
        FROM index_prices
        WHERE ticker = $1
        AND (timestamp, id) < ($2, $3)
        ORDER BY timestamp DESC, id DESC
        LIMIT $4
    """
    assert normalize_sql(query) == normalize_sql(expected_sql)
    assert args == ["TSLA", 1713541200, 42, 50]


@pytest.mark.parametrize(
    "last_created_at, last_id",
    [
        (1713541200, None),  # Передан только timestamp
        (None, 42),  # Передан только ID
    ],
)
def test_build_query_validation_error(last_created_at, last_id):
    """Тест на вызов исключения, если передан только один из параметров курсора."""
    with pytest.raises(ValueError, match="Both 'last_created_at' and 'last_id' must be provided together"):
        PriceRepository._build_query_for_all("BTC", last_created_at, last_id, None)
