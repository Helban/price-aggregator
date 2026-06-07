"""Endpoint tests for the FastAPI web UI.

The scrapers and Vision call are mocked: these tests verify routing, request
validation and that the search query flows through to the rendered page — not
the scrapers or the live API (those are covered elsewhere / are external).
"""
from decimal import Decimal

from fastapi.testclient import TestClient

import app as app_module
from app import app
from models import Product

client = TestClient(app)


def test_index_renders():
    r = client.get("/")
    assert r.status_code == 200
    assert "Aggregator" in r.text
    assert "dropzone" in r.text


def test_empty_search_redirects_to_index():
    r = client.get("/search", params={"q": "   "})
    assert r.status_code == 200  # redirect followed to index
    assert "dropzone" in r.text


def test_search_renders_results(monkeypatch):
    async def fake_search_all(query):
        return [Product(name="Laptop X", price=Decimal("1999.00"),
                        url="https://example.com/x", source="Ceneo")]

    monkeypatch.setattr(app_module, "search_all", fake_search_all)

    r = client.get("/search", params={"q": "laptop"})
    assert r.status_code == 200
    assert "laptop" in r.text          # query echoed in results header
    assert "Laptop X" in r.text        # product rendered


def test_resolve_image_returns_query(monkeypatch):
    async def fake_image_to_query(image_bytes):
        return "iphone 15 pro"

    monkeypatch.setattr(app_module, "image_to_query", fake_image_to_query)

    r = client.post("/resolve-image",
                    files={"file": ("photo.png", b"\x89PNG fake", "image/png")})
    assert r.status_code == 200
    assert r.json() == {"query": "iphone 15 pro"}


def test_resolve_image_unrecognised(monkeypatch):
    async def fake_image_to_query(image_bytes):
        return None

    monkeypatch.setattr(app_module, "image_to_query", fake_image_to_query)

    r = client.post("/resolve-image",
                    files={"file": ("photo.png", b"\x89PNG fake", "image/png")})
    assert r.status_code == 200
    assert r.json() == {"query": None}


def test_resolve_image_rejects_non_image():
    r = client.post("/resolve-image",
                    files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_resolve_image_rejects_oversized(monkeypatch):
    monkeypatch.setattr(app_module, "MAX_IMAGE_BYTES", 10)
    r = client.post("/resolve-image",
                    files={"file": ("big.png", b"x" * 50, "image/png")})
    assert r.status_code == 413
