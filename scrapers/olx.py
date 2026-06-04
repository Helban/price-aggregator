import asyncio
from decimal import Decimal, InvalidOperation
from typing import List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from models import Product
from scrapers.base import ScraperBase

_BASE = "https://www.olx.pl"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9",
}
_NO_THUMBNAIL = "no_thumbnail"


class OlxScraper(ScraperBase):
    source_name = "OLX"

    def __init__(self, fetch_images: bool = True) -> None:
        self._client = httpx.AsyncClient(
            headers=_HEADERS, follow_redirects=True, timeout=15.0
        )
        self._fetch_images = fetch_images

    async def search(self, query: str, limit: int = 20) -> List[Product]:
        slug = quote_plus(query)
        resp = await self._client.get(f"{_BASE}/oferty/q-{slug}/")
        if not resp.is_success:
            raise RuntimeError(f"OLX {resp.status_code}: {resp.text[:200]}")

        products = self._parse(resp.text, limit)

        if self._fetch_images:
            await self._enrich_images(products)

        return products

    def _parse(self, html: str, limit: int) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("[data-cy='l-card']")[:limit]
        return [p for p in (self._parse_card(c) for c in cards) if p]

    def _parse_card(self, card) -> Optional[Product]:
        link = card.find("a", href=True)
        if not link:
            return None
        url = link["href"]
        if not url.startswith("http"):
            url = _BASE + url

        title_el = card.find("h4") or card.find("h3") or card.find("h6")
        if not title_el:
            return None
        name = title_el.get_text(strip=True)

        price_el = card.find(attrs={"data-testid": "ad-price"})
        price = self._parse_price(price_el.get_text(strip=True) if price_el else "")
        if price is None:
            return None

        loc_el = card.find(attrs={"data-testid": "location-date"})
        location = self._parse_location(loc_el.get_text(strip=True) if loc_el else None)

        img = card.find("img")
        image_url = self._valid_image(img.get("src") if img else None)

        return Product(
            name=name,
            price=price,
            url=url,
            source=self.source_name,
            image_url=image_url,
            location=location,
        )

    async def _enrich_images(self, products: List[Product]) -> None:
        """Fetch offer detail pages in parallel to retrieve all photos."""
        async def fetch_one(product: Product) -> None:
            try:
                resp = await self._client.get(product.url, timeout=10.0)
                if resp.is_success:
                    product.image_urls = self._extract_detail_images(resp.text)
                    if product.image_urls and not product.image_url:
                        product.image_url = product.image_urls[0]
            except Exception:
                pass  # image enrichment is best-effort

        await asyncio.gather(*[fetch_one(p) for p in products])

    @staticmethod
    def _extract_detail_images(html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        imgs: list[str] = []
        # OLX detail page: images in swiper/gallery divs
        for img in soup.select("div[data-testid='ad-photo'] img, .swiper-slide img, [data-cy='ad-photo'] img"):
            src = img.get("src") or img.get("data-src", "")
            if src and _NO_THUMBNAIL not in src and src.startswith("http"):
                # request largest variant: drop size param
                base = src.split(";s=")[0]
                if base not in imgs:
                    imgs.append(base)
        return imgs

    @staticmethod
    def _valid_image(src: Optional[str]) -> Optional[str]:
        if not src or _NO_THUMBNAIL in src:
            return None
        return src

    @staticmethod
    def _parse_price(raw: str) -> Optional[Decimal]:
        cleaned = (
            raw.replace("zł", "")
            .replace("\xa0", "")
            .replace(" ", "")
            .replace(",", ".")
            .strip()
        )
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None  # "Zamień", "Negocjuj", "Za darmo", etc.

    @staticmethod
    def _parse_location(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        return raw.split(" - ")[0].strip()

    async def close(self) -> None:
        await self._client.aclose()
