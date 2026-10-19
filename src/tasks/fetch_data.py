import asyncio
from decimal import Decimal
from typing import Any, List, Literal, Type

import aiohttp
from aiohttp import ClientSession
from pydantic import BaseModel, model_validator

from config import config


class FetchResultModel(BaseModel):
    estimated_delivery_price: Decimal
    index_price: Decimal


class FetchModel(BaseModel):
    usIn: int
    usOut: int
    usDiff: int
    result: FetchResultModel
    index_name: str

    @model_validator(mode="before")
    @classmethod
    def inject_context_data(cls, data: Any, info: Any) -> Any:
        if info.context and isinstance(data, dict):
            data.update(info.context)
        return data


async def _fetch_url[T: BaseModel](
    session: ClientSession,
    index_name: Literal["btc_usd", "eth_usd"],
    model: Type[T],
) -> T:
    url = f"{config.API_URL}/public/get_index_price?index_name={index_name}"

    async with session.get(url) as response:
        # TODO логировать, если не смогли получить или конвертнуть в модель
        text = await response.text()
        return model.model_validate_json(text, context={"index_name": index_name})


async def get_prices() -> List[FetchModel]:
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_url(session, index_name, FetchModel) for index_name in ("btc_usd", "eth_usd")]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [result for result in results if isinstance(result, FetchModel)]


if __name__ == "__main__":
    print(asyncio.run(get_prices()))
