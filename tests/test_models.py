from decimal import Decimal

import pytest

from models import Receipt, parse_amount




@pytest.mark.parametrize("raw, expected", [
    ("43.636", Decimal("43636")),
    ("3,000", Decimal("3000")),
    ("1.234,56", Decimal("1234.56")),
    ("1,234.56", Decimal("1234.56")),
    ("12,50", Decimal("12.50")),
    ("4.5", Decimal("4.5")),
    ("0.125", Decimal("0.125")),
    ("Rp 43.636", Decimal("43636")),
])
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


def test_receipt_accepts_separators_in_model_output():
    receipt = Receipt.model_validate({
        "products": [{"name": "BASO", "unit_price": "43.636", "line_total": "43.636"}],
        "total": "46,636",
    })
    assert receipt.total == Decimal("46636")
    assert receipt.products[0].line_total == Decimal("43636")