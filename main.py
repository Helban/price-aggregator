import asyncio
import sys
import tempfile
import webbrowser
from pathlib import Path

from search_service import export_to_excel, render_results, search_all


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
