from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

from models import Product

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9",
}
_TIMEOUT = 15.0


def parse_polish_price(raw: str) -> Decimal | None:
    # formats: "999 zł", "1 234 zł", "1.234,99 zł", "14,99 zł"
    cleaned = raw.replace("zł", "").replace("\xa0", "").strip()
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(" ", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(" ", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


class ScraperBase(ABC):
    source_name: str = ""

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[Product]:
        ...

    async def close(self) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
