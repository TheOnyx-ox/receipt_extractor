from decimal import Decimal
from pathlib import Path
from typing import List


from receipt_extractor.models  import Receipt, Item
import json
import os

import re

ROOT = Path(__file__).resolve().parent.parent / "data" / "cord_test"

SAVE_DIR = Path(__file__).resolve().parent.parent / "data" / "converted_cord"

os.makedirs(f"{SAVE_DIR}", exist_ok=True)

def first_value(value):
    return value[0] if isinstance(value, list) else value

def to_decimal(value):
    value = first_value(value)
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    return Decimal(digits) if digits else None


def as_list(value):
    if value is None:
        return []
    return [value] if isinstance(value, dict) else value


for file in ROOT.glob("*.json"):
    with file.open() as f:
        content = json.load(f)
    print(file.stem)

    gt = content.get("gt_parse")
    sub_total = gt.get("sub_total", {})
    total = gt.get("total", {})
    items = content.get("gt_parse").get("menu")

    products : List[Item] = []
    for item in as_list(items):
        subs = item.get("sub", [])
        for subitem in as_list(subs):
            sub_qty = to_decimal(subitem.get("cnt")) or Decimal(1)
            sub_price = to_decimal(subitem.get("price")) or Decimal(0)

            products.append(Item(
                name=subitem.get("nm"),
                quantity=sub_qty,
                line_total=sub_price,
                unit_price= sub_price / sub_qty
            ))

        quantity = to_decimal(item.get("cnt")) or Decimal(1)
        unit_price = to_decimal(item.get("unitprice"))
        price = to_decimal(item.get("price"))

        if price is None:
            price = quantity * (unit_price or Decimal(1))

        products.append(Item(
            name = item.get("nm"),
            quantity=quantity,
            line_total = price,
            unit_price = price / quantity,
        ))

    total_price = first_value(total.get("total_price"))
    total_value = to_decimal(total_price)

    if total_value is None:
        total_value = sum((product.line_total for product in  products), Decimal(0))

    currency = None
    if total_price is not None:
        currency = re.sub(r"[^A-Za-z]", "", str(total_price)).upper() or None


    receipt = Receipt(
        products = products,
        subtotal = to_decimal(sub_total.get("subtotal_price")),
        tax = to_decimal(sub_total.get("tax_price")),
        total=total_value,
        cash = to_decimal(total.get("cashprice")),
        change = to_decimal(total.get("changeprice")),
        currency = currency,
        discount = to_decimal(sub_total.get("discount_price")) or Decimal(0),
        card = to_decimal(total.get("creditcardprice")) or Decimal(0),
        service_charge = to_decimal(sub_total.get("service_price")),
    )

    Path(str(SAVE_DIR) + "/" + f"{file.stem}.json").write_text(receipt.model_dump_json(indent=2))
