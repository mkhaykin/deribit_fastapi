import logging
from decimal import Decimal

import pytest

from config import config
from tasks.schemas import PriceSnapshot
from tasks.store_data import store_prices


def test_store_prices_success(pg_sync_conn, caplog):
    """Сценарий 1: Успешная первичная вставка валидных данных"""
    test_logger = logging.getLogger("test_logger")
    caplog.set_level(logging.DEBUG, logger="test_logger")

    items = [
        PriceSnapshot(ticker="btc_usd", price=Decimal("65000.50"), ts=1700000000),
        PriceSnapshot(ticker="eth_usd", price=Decimal("3500.25"), ts=1700000000),
    ]

    result = store_prices(items, logger=test_logger)

    assert result is True

    with pg_sync_conn.cursor() as cur:
        cur.execute("SELECT ticker, price, timestamp FROM index_prices ORDER BY ticker ASC")
        records = cur.fetchall()

        assert len(records) == 2

        assert records[0][0] == "btc_usd"
        assert records[0][1] == Decimal("65000.50")
        assert records[0][2] == 1700000000

        assert records[1][0] == "eth_usd"
        assert records[1][1] == Decimal("3500.25")
        assert records[1][2] == 1700000000

    assert "Stored 2 price record(s)" in caplog.text


def test_store_prices_duplicate_insertion(pg_sync_conn):
    """повторная вставка (пока без уникальных индексов делаем дубли)"""
    items = [PriceSnapshot(ticker="btc_usd", price=Decimal("65000.50"), ts=1700000000)]

    assert store_prices(items) is True
    assert store_prices(items) is True

    with pg_sync_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM index_prices WHERE ticker = 'btc_usd'")
        count = cur.fetchone()[0]
        assert count == 2


def test_store_prices_empty_list(pg_sync_conn, caplog):
    """пустой список данных"""
    test_logger = logging.getLogger("test_logger")
    caplog.set_level(logging.WARNING, logger="test_logger")

    result = store_prices([], logger=test_logger)

    assert result is True
    assert "No price data was collected. Skipping database store." in caplog.text

    with pg_sync_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM index_prices")
        count = cur.fetchone()[0]
        assert count == 0


def test_store_prices_invalid_object_type(pg_sync_conn, caplog):
    """передача объекта неверного типа"""
    test_logger = logging.getLogger("test_logger")
    caplog.set_level(logging.ERROR, logger="test_logger")

    bad_items = [{"ticker": "btc_usd", "price": 100, "ts": 123}]

    # в цикле `item.ticker` упадет на словаре
    with pytest.raises(AttributeError):
        store_prices(bad_items, logger=test_logger)


def test_store_prices_database_error_handling(caplog):
    """ошибка базы данных (неверный DSN)"""
    # ломаем DSN перед вызовом функции
    config.DATABASE_DSN = "postgresql://bad_user:bad_pass@localhost:9999/bad_db"

    test_logger = logging.getLogger("test_logger")
    caplog.set_level(logging.ERROR, logger="test_logger")

    items = [PriceSnapshot(ticker="btc_usd", price=Decimal("65000.0"), ts=1700000000)]

    result = store_prices(items, logger=test_logger)

    assert result is False
    assert "Failed to store 1 price record(s)" in caplog.text
