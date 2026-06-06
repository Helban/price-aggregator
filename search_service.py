"""Core search pipeline shared by the CLI (main.py) and the web app (app.py).

Holds the scraping, rendering and export logic so both entry points stay thin.
"""
import asyncio
import sys
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from models import Product
from scrapers.allegro import AllegroScraper  # noqa: F401  (kept for when DataDome is resolved)
from scrapers.ceneo import CeneoScraper
from scrapers.olx import OlxScraper
from scrapers.sprzedajemy import SprzedajemyScraper

# Build the Jinja environment once at import time — the web app renders on every
# request, so re-creating it per call (as the old CLI did) would be wasteful.
_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=True,
)


async def search_all(query: str) -> list[Product]:
    """Run all active scrapers concurrently and return products sorted by price."""
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
    """Render the results page HTML for a query and its products."""
    template = _env.get_template("results.html")
    sources = sorted({p.source for p in products})
    return template.render(query=query, products=products, sources=sources)


def export_to_excel(query: str, products: list[Product], path: Path) -> None:
    """Write products to an .xlsx file with friendly Polish column headers."""
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
