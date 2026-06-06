# Roadmap

## Done
- [x] Ceneo scraper (httpx + BeautifulSoup)
- [x] OLX scraper (httpx + BeautifulSoup, image carousel)
- [x] Sprzedajemy.pl scraper (httpx + BeautifulSoup — JS not required)
- [x] Excel export (`--export` flag, pandas + openpyxl)
- [x] Fixture-based test suite with `update_fixtures.py`
- [x] GitHub Actions CI
- [x] Web UI — FastAPI (`GET /` , `GET /search?q=...` , `POST /resolve-image`)
- [x] Image search — Google Vision WEB_DETECTION turns a pasted/dropped image into a query

## Planned

### Web
- [ ] Deploy to Railway.app (server-side Vision key → visitors test image search with no setup)

### Filters & UI
- [ ] City/location filter — `location` field already present in OLX and Sprzedajemy results
- [ ] Price range slider — min/max filter, client-side
- [ ] Condition filter — new / used (Ceneo already exposes this field)

### Features
- [ ] Price history — SQLite storage, track how prices change over time for a query
- [ ] Price drop alerts — notify (email or desktop) when a product falls below a set threshold
- [ ] REST API — expose scraper results as JSON so other tools can consume them

### More sources
- [ ] Vinted
- [ ] Amazon.pl
- [ ] RTV Euro AGD / Media Expert
- [ ] (plugin architecture already supports adding new scrapers with ~50 lines each)

## Known issues
- [ ] Allegro blocked by DataDome captcha in headless mode
      - options: paid captcha-solving service (CapSolver), apply for API verification
