import logging
from typing import List

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from config import config
from null_logger import NullLogger
from tasks.schemas import PriceSnapshot


def store_prices(
    items: List[PriceSnapshot],
    logger: logging.Logger | None = None,
) -> bool:
    log = logger or NullLogger(__name__)

    if not items:
        log.warning("No price data was collected. Skipping database store.")
        return True

    stmt = sql.SQL(
        """INSERT INTO index_prices (ticker, price, timestamp) VALUES %s""",
    )
    data = [(item.ticker, item.price, item.ts) for item in items]

    try:
        with psycopg2.connect(
            dsn=config.DATABASE_DSN,
        ) as conn:
            log.debug(stmt.as_string(conn))

            with conn.cursor() as cur:
                execute_values(cur, stmt, data)
    except psycopg2.Error as e:
        log.error("Failed to store %d price record(s): %s", len(items), e)
        return False

    log.debug("Stored %d price record(s)", len(items))
    return True
