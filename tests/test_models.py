from decimal import Decimal
import pytest
from models import Product


def make_product(**kwargs) -> Product:
    defaults = dict(name="Test", price=Decimal("999.00"), url="https://example.com", source="Test")
    return Product(**{**defaults, **kwargs})


class TestProductDisplay:
    def test_price_display(self):
        p = make_product(price=Decimal("1234.99"))
        assert p.price_display == "1234.99 zł"

    def test_shipping_display_free(self):
        p = make_product(shipping_price=Decimal("0"))
        assert p.shipping_display == "Darmowa"

    def test_shipping_display_paid(self):
        p = make_product(shipping_price=Decimal("14.99"))
        assert p.shipping_display == "14.99 zł"

    def test_shipping_display_unknown(self):
        p = make_product(shipping_price=None)
        assert p.shipping_display == "?"

    def test_total_price_with_shipping(self):
        p = make_product(price=Decimal("100.00"), shipping_price=Decimal("14.99"))
        assert p.total_price == Decimal("114.99")

    def test_total_price_free_shipping(self):
        p = make_product(price=Decimal("100.00"), shipping_price=Decimal("0"))
        assert p.total_price == Decimal("100.00")

    def test_total_price_no_shipping(self):
        p = make_product(price=Decimal("100.00"), shipping_price=None)
        assert p.total_price == Decimal("100.00")


class TestConditionDisplay:
    def test_new(self):
        p = make_product(condition="NEW")
        assert p.condition_display == "Nowy"

    def test_used(self):
        p = make_product(condition="USED")
        assert p.condition_display == "Używany"

    def test_unknown(self):
        p = make_product(condition=None)
        assert p.condition_display == ""
