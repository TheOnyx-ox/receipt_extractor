from decimal import Decimal
from typing import List, Annotated

from pydantic import BaseModel, Field, BeforeValidator
import re


def parse_amount(value):
    if value is None or isinstance(value, (int, float, Decimal)):
        return value
    s = re.sub(r"[^\d.,\-]", "", str(value))
    if not s:
        return None
    last = max(s.rfind("."), s.rfind(","))
    if last == -1:
        return Decimal(s)
    head, after = s[:last], s[last + 1:]
    both_kinds = "." in s and "," in s
    if both_kinds or len(after) != 3 or head.lstrip("-") in ("", "0"):
        return Decimal(re.sub(r"[.,]", "", head) + "." + after)
    return Decimal(re.sub(r"[.,]", "", s))


Money = Annotated[Decimal, BeforeValidator(parse_amount), Field(ge=0,decimal_places=3)]

class Item(BaseModel):
    name : str
    unit_price: Money  | None = None
    quantity : Decimal = Field(gt=0, description="Quantity of the item", default=Decimal(1))
    line_total : Money


class Receipt(BaseModel):
    products : List[Item] = Field(min_length=1, description="List of products")
    subtotal: Money | None = None
    total: Money
    cash:  Money | None = None
    card: Money | None = None
    change: Money | None = None
    currency: str | None = Field(pattern=r"^[A-Z]{1,3}$", default=None)
    tax: Money | None = None
    service_charge: Money | None = None
    discount: Money | None = None



