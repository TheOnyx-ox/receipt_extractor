from decimal import Decimal

from models import Receipt
from validators import validate


def make_receipt(**overrides):
    data = {
        "products": [
            {"name": "COFFEE", "quantity": 2, "unit_price": "41000", "line_total": "82000"},
            {"name": "CAKE", "quantity": 1, "unit_price": "51000", "line_total": "51000"},
        ],
        "subtotal": "133000",
        "discount": "13300",
        "total": "119700",
        "cash": "120000",
        "change": "300",
    }
    data.update(overrides)
    return Receipt.model_validate(data)


def test_correct_receipt_has_no_issues():
    assert validate(make_receipt())["issues"] == []


def test_wrong_subtotal_is_flagged():
    assert "validate_subtotal" in validate(make_receipt(subtotal="140000"))["issues"]


def test_wrong_total_is_flagged():
    assert "validate_total" in validate(make_receipt(total="119000"))["issues"]


def test_wrong_change_is_flagged():
    assert validate(make_receipt(change="1000"))["issues"] == ["validate_change"]


def test_wrong_line_math_is_flagged():
    receipt = make_receipt(products=[
        {"name": "COFFEE", "quantity": 2, "unit_price": "41000", "line_total": "80000"},
    ])
    assert "validate_products" in validate(receipt)["issues"]


def test_missing_fields_are_skipped_not_failed():
    result = validate(make_receipt(subtotal=None, cash=None, change=None))
    assert result["checks"]["validate_subtotal"] is None
    assert result["checks"]["validate_total"] is None
    assert result["checks"]["validate_change"] is None
    assert result["issues"] == []


def test_validate_does_not_change_the_receipt():
    receipt = make_receipt(total="119000")
    validate(receipt)
    assert receipt.total == Decimal("119000")