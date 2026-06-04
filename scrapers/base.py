from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from models import Product


class ScraperBase(ABC):
    source_name: str = ""

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[Product]:
        ...

    async def close(self) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    @staticmethod
    def parse_polish_price(raw: str) -> Optional[Decimal]:
        """Parse a Polish-formatted price string to Decimal.

        Handles: "999 zł", "1 234 zł", "1.234,99 zł", "14,99 zł".
        Returns None for non-numeric values ("Zamień", "Negocjuj", etc.).
        """
        cleaned = raw.replace("zł", "").replace("\xa0", "").strip()
        if "," in cleaned:
            # Polish decimal separator is comma; dots and spaces are thousands separators
            cleaned = cleaned.replace(".", "").replace(" ", "").replace(",", ".")
        else:
            # Integer price — spaces are thousands separators
            cleaned = cleaned.replace(" ", "")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
