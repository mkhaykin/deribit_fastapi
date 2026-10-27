from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, TypedDict


class IndexRequestTask(TypedDict):
    # что и где запросить
    index_name: Literal["btc_usd", "eth_usd"]
    url: str


class PriceTransferPayload(TypedDict):
    # для типизации данных при передаче между тасками в celery
    ticker: str
    price: str
    ts: int


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    # объект для записи в базу
    ticker: str
    price: Decimal
    ts: int

    def to_payload(self) -> PriceTransferPayload:
        return {
            "ticker": self.ticker,
            "price": str(self.price),
            "ts": self.ts,
        }

    @classmethod
    def from_payload(cls, data: PriceTransferPayload) -> "PriceSnapshot":
        return cls(
            ticker=data["ticker"],
            price=Decimal(data["price"]),
            ts=int(data["ts"]),
        )
