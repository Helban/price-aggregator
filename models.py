from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Product:
    name: str
    price: Decimal
    url: str
    source: str
    image_url: Optional[str] = None
    condition: Optional[str] = None   # 'NEW' | 'USED' | None
    seller: Optional[str] = None
    shipping_price: Optional[Decimal] = None
    location: Optional[str] = None

    @property
    def total_price(self) -> Decimal:
        return self.price + (self.shipping_price or Decimal("0"))

    @property
    def price_display(self) -> str:
        return f"{self.price:.2f} zł"

    @property
    def shipping_display(self) -> str:
        if self.shipping_price is None:
            return "?"
        if self.shipping_price == 0:
            return "Darmowa"
        return f"{self.shipping_price:.2f} zł"

    @property
    def condition_display(self) -> str:
        return {"NEW": "Nowy", "USED": "Używany"}.get(self.condition or "", self.condition or "")
