import asyncio
import sys
import tempfile
import webbrowser
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from models import Product
from scrapers.allegro import AllegroScraper
from scrapers.ceneo import CeneoScraper
from scrapers.olx import OlxScraper
from scrapers.sprzedajemy import SprzedajemyScraper


async def search_all(query: str) -> list[Product]:
    scrapers = [
        # AllegroScraper(),  # blocked by DataDome — to be resolved
        CeneoScraper(),
        OlxScraper(fetch_images=True),
        SprzedajemyScraper(),
    ]
    try:
        results = await asyncio.gather(
            *(s.search(query, limit=30) for s in scrapers),
            return_exceptions=True,
        )
    finally:
        for s in scrapers:
            try:
                await s.close()
            except Exception:
                pass

    products: list[Product] = []
    for r in results:
        if isinstance(r, Exception):
            print(f"[scraper error] {r}", file=sys.stderr)
        else:
            products.extend(r)

    return sorted(products, key=lambda p: p.price)


def render_results(query: str, products: list[Product]) -> str:
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=True,
    )
    template = env.get_template("results.html")
    sources = sorted({p.source for p in products})
    return template.render(query=query, products=products, sources=sources)


def export_to_excel(query: str, products: list[Product], path: Path) -> None:
    rows = [
        {
            "Nazwa": p.name,
            "Cena (zł)": float(p.price),
            "Dostawa (zł)": float(p.shipping_price) if p.shipping_price is not None else "",
            "Łącznie (zł)": float(p.total_price),
            "Źródło": p.source,
            "Stan": p.condition_display or "",
            "Lokalizacja": p.location or "",
            "Sprzedawca": p.seller or "",
            "URL": p.url,
        }
        for p in products
    ]
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=query[:31])
        ws = writer.sheets[query[:31]]
        ws.column_dimensions["A"].width = 55
        ws.column_dimensions["I"].width = 60
    print(f"Exported: {path}")


def open_in_browser(html: str) -> None:
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(html)
        path = f.name
    webbrowser.open(f"file://{path}")
    print(f"Opened: {path}")


async def main() -> None:
    args = sys.argv[1:]
    export = "--export" in args
    query = " ".join(a for a in args if a != "--export").strip()

    if not query:
        print("Usage: python main.py <query> [--export]")
        sys.exit(1)

    print(f"Searching: {query!r}")
    products = await search_all(query)
    print(f"Found {len(products)} results")

    html = render_results(query, products)
    open_in_browser(html)

    if export:
        safe = query.replace(" ", "_")[:40]
        export_to_excel(query, products, Path(f"{safe}.xlsx"))


if __name__ == "__main__":
    asyncio.run(main())
