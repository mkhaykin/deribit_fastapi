from decimal import Decimal

import pytest
from pydantic import ValidationError

from api.schemas import IndexPriceResponse


def test_response_accepts_valid_data() -> None:
    response = IndexPriceResponse(
        id=1,
        ticker="BTC",
        price="123.456789",
        timestamp=1_760_000_000,
    )

    assert response.id == 1
    assert response.ticker == "BTC"
    assert response.price == Decimal("123.456789")


def test_response_rejects_invalid_id() -> None:
    with pytest.raises(ValidationError):
        IndexPriceResponse(
            id="not-an-integer",
            ticker="BTC",
            price="123.45",
            timestamp=1_760_000_000,
        )
