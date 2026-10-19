from dataclasses import dataclass
from decimal import Decimal
from typing import List

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from config import config


@dataclass(frozen=True, slots=True)
class DTO:
    ticker: str
    price: Decimal
    ts: int


def store_prices(items: List[DTO]) -> None:
    stmt = sql.SQL(
        """INSERT INTO index_prices (ticker, price, timestamp) VALUES %s""",
    )
    data = [(item.ticker, item.price, item.ts) for item in items]

    with psycopg2.connect(
        dsn=config.DATABASE_DSN,
    ) as conn:
        conn.set_session(autocommit=True)
        with conn.cursor() as cur:
            execute_values(cur, stmt, data)

    for dto in items:
        print(dto)
