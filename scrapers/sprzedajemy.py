import httpx
from bs4 import BeautifulSoup

from models import Product
from scrapers.base import ScraperBase, _HEADERS, _TIMEOUT, parse_polish_price

_BASE = "https://sprzedajemy.pl"


class SprzedajemyScraper(ScraperBase):
    source_name = "Sprzedajemy"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers=_HEADERS, follow_redirects=True, timeout=_TIMEOUT
        )

    async def search(self, query: str, limit: int = 20) -> list[Product]:
        resp = await self._client.get(
            f"{_BASE}/szukaj",
            params={
                "schm2": "hp",
                "inp_text[v]": query,
                "catCode": "",
            },
        )
        if not resp.is_success:
            raise RuntimeError(f"Sprzedajemy {resp.status_code}: {resp.text[:200]}")
        return self._parse(resp.text, limit)

    def _parse(self, html: str, limit: int) -> list[Product]:
        soup = BeautifulSoup(html, "lxml")
        articles = soup.select("article.element")[:limit]
        return [p for p in (self._parse_article(a) for a in articles) if p]

    def _parse_article(self, article) -> Product | None:
        link = article.select_one("a.offerLink")
        if not link:
            return None
        url = link["href"]
        if not url.startswith("http"):
            url = _BASE + url

        title_el = article.select_one("h2.title a")
        if not title_el:
            return None
        name = title_el.get_text(strip=True)

        price_el = article.select_one(".price")
        price = parse_polish_price(price_el.get_text(strip=True) if price_el else "")
        if price is None:
            return None

        city_el = article.select_one(".city")
        location = city_el.get_text(strip=True) if city_el else None

        img = article.select_one("img")
        image_url = img.get("src") if img else None

        return Product(
            name=name,
            price=price,
            url=url,
            source=self.source_name,
            image_url=image_url,
            location=location,
        )

    async def close(self) -> None:
        await self._client.aclose()
