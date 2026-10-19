from decimal import Decimal

from pydantic import BaseModel, Field


class IndexPriceResponse(BaseModel):
    id: int
    ticker: str = Field(..., description="Тикер валюты")
    price: Decimal = Field(..., description="Цена с высокой точностью")
    timestamp: int = Field(..., description="UNIX timestamp времени сохранения")
