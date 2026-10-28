"""
index
"""

from yoyo import step

__depends__ = {"20261015_01_OVs7V-initial"}

steps = [
    step(
        (
            "CREATE INDEX IF NOT EXISTS idx__index_prices__latest_by_ticker "
            "ON index_prices(ticker, timestamp DESC, id DESC);"
        ),
        "DROP INDEX IF EXISTS idx__index_prices__latest_by_ticker;",
    ),
]
