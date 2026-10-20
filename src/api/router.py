import logging
from datetime import date
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .schemas import IndexPriceResponse
from .services import PriceService

router = APIRouter()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_pg_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def get_price_service(
    pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)],
) -> PriceService:
    return PriceService(pool=pool, logger=logger)


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
    ans = await service.get_latest_by_ticker(ticker)
    if ans is None:
        raise HTTPException(status_code=404, detail=f"No data found for ticker {ticker}")
    return ans


@router.get("/filter")
async def get_prices_by_date(
    ticker: Annotated[str, Query(..., description="Тикер валюты, например 'BTC'")],
    target_date: Annotated[date, Query(..., alias="date", description="Дата для фильтрации (YYYY-MM-DD)")],
    service: Annotated[PriceService, Depends(get_price_service)],
) -> list[IndexPriceResponse]:
    """Получение цены валюты с фильтром по конкретной дате."""
    return await service.get_by_ticker_and_date(ticker, target_date)
