import base64
import json
import logging
from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from pydantic import BaseModel, Field

from ..helpers import build_next_link, get_price_service
from ..schemas import IndexPriceResponse
from ..services.price import PriceService

router = APIRouter()

logger = logging.getLogger(__name__)


class PriceCursor(BaseModel):
    timestamp: int = Field(0, ge=0, alias="t")
    row_id: int = Field(0, ge=0, alias="i")


def encode_cursor(timestamp: int, row_id: int) -> str:
    cursor_data = json.dumps({"t": timestamp, "i": row_id})
    return base64.urlsafe_b64encode(cursor_data.encode()).decode()


def decode_cursor(cursor_str: str) -> PriceCursor:
    decoded = base64.urlsafe_b64decode(cursor_str.encode()).decode()
    return PriceCursor.model_validate_json(decoded)


@router.get(
    "/all",
    description=(
        "Returns a paginated list of historical index prices "
        "for the specified ticker, ordered from newest to oldest."
    ),
)
async def get_all_prices(  # noqa: PLR0913, PLR0917
    service: Annotated[PriceService, Depends(get_price_service)],
    request: Request,
    response: Response,
    ticker: Annotated[str, Query(..., description="Тикер валюты, например 'BTC'")],
    cursor: str = Query(None, description="Параметры курсора ..."),
    limit: int = Query(100, ge=1, le=10_000, description="Количество возвращаемых записей"),
) -> list[IndexPriceResponse]:
    """Получение всех сохраненных данных по указанной валюте."""
    last_timestamp, last_id = None, None
    if cursor:
        try:
            price_cursor = decode_cursor(cursor)
            last_timestamp = price_cursor.timestamp
            last_id = price_cursor.row_id

            logger.debug("Декодировали параметры: last_timestamp=%d, last_id=%d", last_timestamp, last_id)
        except Exception as e:
            logger.error("Ошибка разбора %s: %s", cursor, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted cursor provided",
            ) from None

    result = await service.get_all_by_ticker(ticker, last_timestamp, last_id, limit)

    if result:
        last_row = result[-1]
        new_cursor = encode_cursor(last_row.timestamp, last_row.id)
        response.headers["X-Next-Cursor"] = new_cursor
        next_link = build_next_link(request, ticker=ticker, limit=limit, cursor=new_cursor)
        response.headers["Link"] = f'<{next_link}>; rel="next"'
    else:
        response.headers["X-Next-Cursor"] = ""
        if "Link" in response.headers:
            del response.headers["Link"]

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
