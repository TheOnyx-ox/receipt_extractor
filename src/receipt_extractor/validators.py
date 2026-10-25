from decimal import Decimal
from pathlib import Path

from models import Receipt
import json

ROOT = Path(__file__).resolve().parent.parent.parent
PREDICTIONS_PATH = ROOT / "data" / "cord_predictions"
CONVERTED_CORD = ROOT / "data" / "converted_cord"

file_path = PREDICTIONS_PATH / 'receipt_000.json'


def validate_subtotal(receipt):
    if receipt.subtotal is not None:
        products = receipt.products
        subtotal = 0
        for product in products:
            subtotal += product.line_total

        if subtotal == receipt.subtotal:
            return True

        return False

    return None

def validate_products(receipt):
    check = None
    for product in receipt.products:
        if product.unit_price is None:
            continue
        if product.line_total != product.unit_price * product.quantity:
            return False
        check = True
    return check


def validate_total(receipt):

    if receipt.tax is not None:
        tax = Decimal(receipt.tax)
    else:
        tax = 0

    if receipt.service_charge is not None:
        service_charge = Decimal(receipt.service_charge)
    else:
        service_charge = 0

    if receipt.discount is not None:
        discount = Decimal(receipt.discount)
    else:
        discount = 0

    if receipt.subtotal is not None and receipt.total is not None:
        receipt_total = receipt.subtotal + tax + service_charge - discount
        if receipt.total == receipt_total:
            return True
        return False

    return None


def validate_change(receipt):
    if receipt.cash is None or receipt.change is None:
        return None
    return receipt.cash - receipt.total == receipt.change


RULES = {
    'validate_subtotal': validate_subtotal,
    'validate_products': validate_products,
    'validate_total': validate_total,
    'validate_change': validate_change
}

def validate(receipt):
    checks = {name: rule(receipt) for name, rule in RULES.items()}
    issues = [name for name, result in checks.items() if result is False]

    return {"checks":checks, "issues":issues}


def main():
    counts = {name: {"passed": 0, "failed": 0, "skipped": 0} for name in RULES}

    for path in sorted(PREDICTIONS_PATH.glob("*.json")):
        receipt = Receipt.model_validate_json(path.read_text())
        result = validate(receipt)
        for name, ok in result["checks"].items():
            key = "skipped" if ok is None else "passed" if ok else "failed"
            counts[name][key] += 1
        if result["issues"]:
            print(path.stem, result["issues"])

    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()