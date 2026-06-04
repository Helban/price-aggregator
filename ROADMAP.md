# Roadmap

## In progress
- [ ] Sprzedajemy.pl scraper (Playwright, JS-rendered)

## Planned
- [ ] Web UI — FastAPI endpoint + search form, deploy to Railway.app
      - `GET /search?q=...` runs scrapers and returns rendered HTML
      - same Jinja2 template, add search bar at the top
      - Ceneo + OLX work out of the box (httpx only, no Playwright needed)

## Known issues
- [ ] Allegro blocked by DataDome captcha in headless mode
      - options: undetected-chromium, residential proxy, apply for API verification
