from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..helpers import get_price_service
from ..schemas import IndexPriceResponse
from ..services.price import PriceService

router = APIRouter()


@router.get("/all", description="Returns up to 1000 most recent records.")
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


@router.get(
    "/filter",
    description="Returns a paginated list of the most recent records filtered by ticker and date.",
)
async def get_prices_by_date(
    service: Annotated[PriceService, Depends(get_price_service)],
    ticker: Annotated[str, Query(..., description="Тикер валюты, например 'BTC'")],
    target_date: Annotated[date, Query(..., alias="date", description="Дата для фильтрации (YYYY-MM-DD)")],
    limit: int = Query(100, ge=1, le=1440, description="Количество возвращаемых записей"),
    offset: int = Query(0, ge=0, description="Смещение от начала выборки"),
) -> list[IndexPriceResponse]:
    """Получение цены валюты с фильтром по конкретной дате."""
    return await service.get_by_ticker_and_date(ticker, target_date, limit, offset)
