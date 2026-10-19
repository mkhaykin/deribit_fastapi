import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from schemas import IndexPriceResponse
from services import PriceService

router = APIRouter()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_price_service() -> PriceService:
    return PriceService(logger=logger)


@router.get("/all")
async def get_all_prices(
    ticker: Annotated[str, Query(..., description="Тикер валюты, например 'BTC'")],
    service: Annotated[PriceService, Depends(get_price_service)],
) -> list[IndexPriceResponse]:
    """Получение всех сохраненных данных по указанной валюте."""
    result = await service.get_all_by_ticker(ticker)
    return result


@router.get("/latest")
async def get_latest_price(
    ticker: Annotated[str, Query(..., description="Тикер валюты, например 'BTC'")],
    service: Annotated[PriceService, Depends(get_price_service)],
) -> IndexPriceResponse:
    """Получение последней цены валюты."""
    return await service.get_latest_by_ticker(ticker)


@router.get("/filter")
async def get_prices_by_date(
    ticker: Annotated[str, Query(..., description="Тикер валюты, например 'BTC'")],
    target_date: Annotated[date, Query(..., alias="date", description="Дата для фильтрации (YYYY-MM-DD)")],
    service: Annotated[PriceService, Depends(get_price_service)],
) -> list[IndexPriceResponse]:
    """Получение цены валюты с фильтром по конкретной дате."""
    return await service.get_by_ticker_and_date(ticker, target_date)
