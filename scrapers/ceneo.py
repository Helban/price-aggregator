from decimal import Decimal
from typing import List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from models import Product
from scrapers.base import ScraperBase

_BASE = "https://www.ceneo.pl"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9",
}


class CeneoScraper(ScraperBase):
    source_name = "Ceneo"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers=_HEADERS, follow_redirects=True, timeout=15.0
        )

    async def search(self, query: str, limit: int = 20) -> List[Product]:
        slug = quote_plus(query)
        resp = await self._client.get(f"{_BASE}/szukaj-{slug}")
        if not resp.is_success:
            raise RuntimeError(f"Ceneo {resp.status_code}: {resp.text[:200]}")
        return self._parse(resp.text, limit)

    def _parse(self, html: str, limit: int) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        rows = soup.select(".cat-prod-row")[:limit]
        return [p for p in (self._parse_row(r) for r in rows) if p]

    def _parse_row(self, row) -> Optional[Product]:
        product_id = row.get("data-productid")
        price_raw = row.get("data-price")
        if not product_id or not price_raw:
            return None

        name_el = row.select_one(".cat-prod-row__name a span")
        name = (
            name_el.get_text(strip=True)
            if name_el
            else row.get("data-productname", "Brak tytułu")
        )

        img = row.select_one(".cat-prod-row__foto img")
        image_url = img["src"] if img else None
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url

        free_ship = row.select_one(".free-delivery-label")
        shipping = Decimal("0") if free_ship else None

        return Product(
            name=name,
            price=Decimal(price_raw),
            url=f"{_BASE}/{product_id}",
            source=self.source_name,
            image_url=image_url,
            shipping_price=shipping,
        )

    async def close(self) -> None:
        await self._client.aclose()
