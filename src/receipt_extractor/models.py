from decimal import Decimal
from typing import List, Annotated

from pydantic import BaseModel, Field

Money = Annotated[Decimal, Field(gt=0,decimal_places=2)]

class Item(BaseModel):
    name : str
    unit_price: Money  | None = None
    quantity : Decimal = Field(gt=0, description="Quantity of the item", default=Decimal(1))
    line_total = Money


class Receipt(BaseModel):
    products : List[Item] = Field(min_length=1, description="List of products")
    subtotal: Money | None = None
    total: Money
    cash:  Money | None = None
    change: Money | None = None
    currency: str = Field(pattern=r"^[A-Z]{3}$", default="None")
    tax: Money | None = None
    service_charge: Money | None = None
    discount: Money | None = None



