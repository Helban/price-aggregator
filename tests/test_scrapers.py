"""
Parser tests using real HTML fixtures captured from each site.

When a scraper breaks due to a site layout change:
1. Re-capture the fixture: python tests/update_fixtures.py
2. Update the parser to match the new structure
3. Re-run tests
"""
from decimal import Decimal
from pathlib import Path

import pytest

from scrapers.ceneo import CeneoScraper
from scrapers.olx import OlxScraper

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestCeneoParser:
    def setup_method(self):
        self.scraper = CeneoScraper()
        self.html = load("ceneo_laptop_lenovo.html")

    def test_returns_results(self):
        products = self.scraper._parse(self.html, limit=20)
        assert len(products) > 0

    def test_respects_limit(self):
        products = self.scraper._parse(self.html, limit=5)
        assert len(products) <= 5

    def test_product_fields(self):
        product = self.scraper._parse(self.html, limit=1)[0]
        assert product.name
        assert product.price > 0
        assert product.url.startswith("https://www.ceneo.pl/")
        assert product.source == "Ceneo"

    def test_price_is_decimal(self):
        products = self.scraper._parse(self.html, limit=5)
        for p in products:
            assert isinstance(p.price, Decimal)

    def test_image_url_is_absolute(self):
        products = self.scraper._parse(self.html, limit=5)
        for p in products:
            if p.image_url:
                assert p.image_url.startswith("https://")

    def test_free_shipping_parsed(self):
        products = self.scraper._parse(self.html, limit=20)
        free = [p for p in products if p.shipping_price == Decimal("0")]
        assert len(free) > 0, "Expected at least one offer with free shipping"


class TestOlxParser:
    def setup_method(self):
        self.scraper = OlxScraper()
        self.html = load("olx_laptop_lenovo.html")

    def test_returns_results(self):
        products = self.scraper._parse(self.html, limit=20)
        assert len(products) > 0

    def test_respects_limit(self):
        products = self.scraper._parse(self.html, limit=3)
        assert len(products) <= 3

    def test_product_fields(self):
        products = self.scraper._parse(self.html, limit=20)
        product = products[0]
        assert product.name
        assert product.price > 0
        assert product.url.startswith("https://www.olx.pl/")
        assert product.source == "OLX"

    def test_location_stripped_of_date(self):
        products = self.scraper._parse(self.html, limit=20)
        located = [p for p in products if p.location]
        assert located, "Expected at least one product with location"
        for p in located:
            assert "Odświeżono" not in p.location
            assert "dnia" not in p.location

    def test_skips_non_numeric_prices(self):
        products = self.scraper._parse(self.html, limit=20)
        for p in products:
            assert isinstance(p.price, Decimal)


class TestOlxPriceParser:
    def setup_method(self):
        self.scraper = OlxScraper()

    @pytest.mark.parametrize("raw,expected", [
        ("999 zł", Decimal("999")),
        ("1 234 zł", Decimal("1234")),
        ("14\xa0999 zł", Decimal("14999")),
        ("1 234,99 zł", Decimal("1234.99")),
    ])
    def test_valid_prices(self, raw, expected):
        assert self.scraper._parse_price(raw) == expected

    @pytest.mark.parametrize("raw", ["Zamień", "Negocjuj", "Za darmo", ""])
    def test_non_numeric_returns_none(self, raw):
        assert self.scraper._parse_price(raw) is None
