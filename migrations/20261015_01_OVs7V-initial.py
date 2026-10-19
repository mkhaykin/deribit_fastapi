"""
initial
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        """
CREATE TABLE IF NOT EXISTS index_prices (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    price NUMERIC(24, 8) NOT NULL,
    timestamp INTEGER NOT NULL)
            """,
        "DROP TABLE index_prices",
    ),
    step(
        "CREATE INDEX IF NOT EXISTS idx_ticker_timestamp ON index_prices(ticker, timestamp)",
        "DROP INDEX IF EXISTS idx_ticker_timestamp",
    ),
]
