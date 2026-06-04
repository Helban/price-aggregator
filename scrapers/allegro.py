import asyncio
from decimal import Decimal
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, BrowserContext

from models import Product
from scrapers.base import ScraperBase

_SEARCH_URL = "https://allegro.pl/listing"

# JS patches applied before page load to mask headless signals
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pl-PL', 'pl', 'en-US', 'en']});
window.chrome = {runtime: {}};
""".strip()


class AllegroScraper(ScraperBase):
    source_name = "Allegro"

    async def search(self, query: str, limit: int = 20) -> list[Product]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx: BrowserContext = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="pl-PL",
                viewport={"width": 1280, "height": 900},
                extra_http_headers={
                    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            await ctx.add_init_script(_STEALTH_JS)
            page = await ctx.new_page()

            try:
                await page.goto(
                    f"{_SEARCH_URL}?string={quote_plus(query)}",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                # DataDome check
                html_check = await page.content()
                if "datadome" in html_check.lower() or "captcha" in html_check.lower():
                    raise RuntimeError(
                        "Allegro zablokował dostęp (DataDome captcha). "
                        "Spróbuj ponownie za chwilę lub uruchom z widoczną przeglądarką."
                    )

                await page.wait_for_selector("article", timeout=15000)
                await asyncio.sleep(0.8)
                html = await page.content()
            finally:
                await browser.close()

        return self._parse(html, limit)

    def _parse(self, html: str, limit: int) -> list[Product]:
        soup = BeautifulSoup(html, "lxml")
        products: list[Product] = []
        for article in soup.find_all("article")[:limit]:
            p = self._parse_article(article)
            if p:
                products.append(p)
        return products

    def _parse_article(self, article) -> Optional[Product]:
        # link z URL oferty i tytułem
        link = article.find("a", href=lambda h: h and "/oferta/" in h)
        if not link:
            return None
        url = link["href"]
        if not url.startswith("http"):
            url = "https://allegro.pl" + url

        name = link.get("title") or link.get_text(strip=True)
        if not name:
            h = article.find(["h2", "h3"])
            name = h.get_text(strip=True) if h else "Brak tytułu"

        # cena: szukamy elementu zawierającego "zł"
        price = self._extract_price(article)
        if price is None:
            return None

        # dostawa
        shipping = self._extract_shipping(article)

        # obrazek
        img = article.find("img")
        image_url = img.get("src") or img.get("data-src") if img else None

        return Product(
            name=name,
            price=price,
            url=url,
            source=self.source_name,
            image_url=image_url,
            shipping_price=shipping,
        )

    @staticmethod
    def _extract_price(article) -> Optional[Decimal]:
        for el in article.find_all(string=True):
            text = el.strip().replace("\xa0", "").replace(" ", "")
            if "zł" in text:
                try:
                    raw = text.replace("zł", "").replace(",", ".").strip()
                    return Decimal(raw)
                except Exception:
                    continue
        return None

    @staticmethod
    def _extract_shipping(article) -> Optional[Decimal]:
        for el in article.find_all(string=True):
            text = el.lower()
            if "darmow" in text or "free" in text:
                return Decimal("0")
        return None
