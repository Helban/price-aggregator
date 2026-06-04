# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Polish Price Aggregator — wyszukuje produkt równolegle na Allegro, Ceneo, OLX i Sprzedajemy.pl,
wyniki prezentuje jako stronę HTML otwieraną w przeglądarce.

## Commands

```bash
source .venv/bin/activate

# Run
python main.py "laptop lenovo"

# Add dependency
pip install <package> && pip freeze > requirements.txt
```

## Architecture

Plugin/strategy pattern — każdy scraper to osobna klasa dziedzicząca z `ScraperBase`.

```
main.py               # entry point: asyncio.gather po wszystkich scraperach → render → webbrowser
config.py             # env vars (ALLEGRO_CLIENT_ID, ALLEGRO_CLIENT_SECRET) via python-dotenv
models.py             # Product dataclass — jeden wspólny model dla wszystkich źródeł
scrapers/
  base.py             # ScraperBase ABC z metodą search(query, limit) → List[Product]
  allegro.py          # REST API (OAuth2 client_credentials), httpx async
  ceneo.py            # TODO: httpx + BeautifulSoup
  olx.py              # TODO: httpx + BeautifulSoup / REST API
  sprzedajemy.py      # TODO: Playwright (JS-rendered)
templates/
  results.html        # Jinja2 — grid kart, filtrowanie po źródle po stronie klienta
```

Nowe scrapery: skopiuj wzorzec z `allegro.py`, nadpisz `source_name` i `search()`, dodaj instancję do listy w `main.py`.

## Allegro API

Wymaga konta deweloperskiego: https://developer.allegro.pl  
Klucze w `.env` (skopiuj z `.env.example`).
Sandbox: zmień `_AUTH_URL`/`_API_BASE` w `scrapers/allegro.py` na `allegrosandbox.pl`.
