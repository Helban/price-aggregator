import asyncio
import sys
import tempfile
import webbrowser
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from models import Product
from scrapers.allegro import AllegroScraper
from scrapers.ceneo import CeneoScraper


async def search_all(query: str) -> list[Product]:
    scrapers = [
        # AllegroScraper(),  # zablokowany przez DataDome — do rozwiązania
        CeneoScraper(),
    ]
    try:
        results = await asyncio.gather(
            *(s.search(query) for s in scrapers),
            return_exceptions=True,
        )
    finally:
        for s in scrapers:
            await s.close()

    products: list[Product] = []
    for r in results:
        if isinstance(r, Exception):
            print(f"[scraper error] {r}", file=sys.stderr)
        else:
            products.extend(r)

    return sorted(products, key=lambda p: p.price)


def render_results(query: str, products: list[Product]) -> str:
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("results.html")
    sources = sorted({p.source for p in products})
    return template.render(query=query, products=products, sources=sources)


def open_in_browser(html: str) -> None:
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(html)
        path = f.name
    webbrowser.open(f"file://{path}")
    print(f"Opened: {path}")


async def main() -> None:
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("Usage: python main.py <query>")
        sys.exit(1)

    print(f"Searching: {query!r}")
    products = await search_all(query)
    print(f"Found {len(products)} results")

    html = render_results(query, products)
    open_in_browser(html)


if __name__ == "__main__":
    asyncio.run(main())
