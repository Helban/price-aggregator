"""
Run this script to refresh HTML fixtures when scrapers break due to site changes:

    python tests/update_fixtures.py
"""
import asyncio
from pathlib import Path

import httpx

FIXTURES = Path(__file__).parent / "fixtures"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
SOURCES = [
    ("ceneo_laptop_lenovo.html",       "https://www.ceneo.pl/szukaj-laptop+lenovo"),
    ("olx_laptop_lenovo.html",         "https://www.olx.pl/oferty/q-laptop-lenovo/"),
    ("sprzedajemy_laptop_lenovo.html", "https://sprzedajemy.pl/szukaj?schm2=hp&inp_text[v]=laptop+lenovo&inp_category_id=5&catCode="),
]


async def main() -> None:
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20.0) as c:
        for filename, url in SOURCES:
            print(f"Fetching {url} ...", end=" ", flush=True)
            resp = await c.get(url)
            path = FIXTURES / filename
            path.write_text(resp.text, encoding="utf-8")
            print(f"{resp.status_code} → {path.name} ({len(resp.text):,} chars)")


if __name__ == "__main__":
    asyncio.run(main())
