from decimal import Decimal
from pathlib import Path
from typing import List


from receipt_extractor.models  import Receipt, Item
import json
import os
ROOT = Path(__file__).resolve().parent.parent / "data" / "cord_test"

import re


# class Receipt(BaseModel):
#     title: str | None = None
#     products : List[Item] = Field(min_length=1, description="List of products")
#     subtotal: Money | None = None
#     total: Money
#     cash:  Money | None = None
#     card: Money | None = None
#     change: Money | None = None
#     currency: str = Field(pattern=r"^[A-Z]{3}$", default="None")
#     tax: Money | None = None
#     service_charge: Money | None = None
#     discount: Money | None = None


for file in ROOT.glob("*.json"):
    content = json.load(file.open())
    print(file.stem)

    items = content.get("gt_parse").get("menu")

    if isinstance(items, dict):
        items = [items]

    products : List[Item] = []
    for item in items:
        subs = item.get("sub", [])
        if isinstance(subs, dict):
            subs = [subs]

        for subitem in subs:
            price = Decimal(re.sub(r"\D", "", subitem.get("price")))
            products.append(Item(
                name=subitem.get("nm"),
                quantity=Decimal(re.sub(r"\D", "", subitem.get("cnt"))) if "cnt" in subitem else Decimal(1),
                line_total=price,
                unit_price= price / Decimal(subitem["cnt"]) if "cnt" in subitem else None
            ))


        quantity = Decimal(re.sub(r"\D", "", item.get("cnt"))) if "cnt" in item else Decimal(1)
        unit_price = Decimal(re.sub(r"\D", "", item.get("unitprice"))) if "unitprice" in item else 1

        price = Decimal(re.sub(r"\D", "", item.get("price"))) if "price" in item else quantity * unit_price

        products.append(Item(
            name = item.get("nm"),
            quantity=quantity,
            line_total = price,
            unit_price = price / quantity,
        ))

    if "total_price" not in content.get("gt_parse").get("total"):
        total_price_calculated = Decimal(0)
        for p in products:
            total_price_calculated += p.line_total
    else:
        total_price_calculated = Decimal(re.sub(r"\D", "", content.get("gt_parse").get("total").get("total_price")))

        letters = str(re.sub(r"[^A-Za-z]", "", content.get("gt_parse").get("total").get("total_price"))).upper() if any(c.isalpha() for c in content.get("gt_parse").get("total").get("total_price")) else None

    sp = content["gt_parse"].get("sub_total", {}).get("subtotal_price")
    dis = content["gt_parse"].get("sub_total").get("discount_price", "0") if "sub_total" in content["gt_parse"] else "0"

    receipt = Receipt(
        products = products,

        subtotal = Decimal(re.sub(r"\D", "", sp[0] if isinstance(sp, list) else sp)) if sp else None,

        tax = Decimal(re.sub(r"\D", "", content.get("gt_parse").get("sub_total").get("tax_price"))) if "sub_total" in content.get("gt_parse") and "tax_price" in content.get("gt_parse").get("sub_total") else None,


        total=total_price_calculated,


        cash=Decimal(re.sub(r"\D", "", content.get("gt_parse").get("total").get("cashprice"))) if "cashprice" in content.get("gt_parse").get("total") else None,


        change=Decimal(re.sub(r"\D", "", content.get("gt_parse").get("total").get("changeprice"))) if "changeprice"  in content.get("gt_parse").get("total") else None,

        currency = letters if letters else None,

        discount = Decimal(re.sub(r"\D", "", dis)) ,

        card = Decimal(re.sub(r"\D", "", content.get("gt_parse").get("total").get("creditcardprice"))) if "creditcardprice"  in content.get("gt_parse").get("total") else Decimal(0),

        service_charge = Decimal(re.sub(r"\D", "", content.get("gt_parse").get("sub_total").get("service_price"))) if "sub_total" in content.get("gt_parse") and "service_price" in content.get("gt_parse").get("sub_total") else None,

    )


    SAVE_DIR = Path(__file__).resolve().parent.parent /"data" / "converted_cord"

    os.makedirs(f"{SAVE_DIR}", exist_ok=True)

    Path(str(SAVE_DIR) + "/" + f"{file.stem}.json").write_text(receipt.model_dump_json(indent=2))
