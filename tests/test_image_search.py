"""Tests for image_search — Vision response parsing and the async call path.

Like the scraper tests, these verify how we parse a realistic Vision response
shape rather than mocking "the API replied". The HTTP layer is exercised with
httpx's built-in MockTransport, so no live API key or network is needed.
"""
import httpx
import pytest

import image_search
from image_search import _extract_query, _pick_from_text, image_to_query


class TestPickFromText:
    """Unit tests for the TEXT_DETECTION text picker."""

    def test_book_cover_phrase_per_line(self):
        # Two words per line — the common layout
        assert _pick_from_text("MAREK KRAJEWSKI\nCZAS ZDRAJCÓW\nznak") == "MAREK KRAJEWSKI CZAS ZDRAJCÓW"

    def test_book_cover_word_per_line(self):
        # Vision puts each word on its own line for large text — real case observed
        assert _pick_from_text("znak\nMAREK\nKRAJEWSKI\nCZAS\nZDRAJCÓW") == "MAREK KRAJEWSKI CZAS ZDRAJCÓW"

    def test_strips_noise_tokens(self):
        assert _pick_from_text("David Wilson\nMordercy\nHELION") == "David Wilson Mordercy"

    def test_only_noise_returns_none(self):
        # All words are noise tokens — nothing left after filtering.
        assert _pick_from_text("znak\nISBN\nPWN") is None

    def test_long_text_capped_at_six_words(self):
        # Even a long line is capped at 6 words and returned as a query.
        result = _pick_from_text("Sony WH-1000XM5 Wireless Noise Cancelling Headphones Black")
        assert result == "Sony WH-1000XM5 Wireless Noise Cancelling Headphones"

    def test_single_word_returns_none(self):
        assert _pick_from_text("ZNAK") is None

    def test_empty_returns_none(self):
        assert _pick_from_text("") is None


class TestExtractQuery:
    """Parsing of the combined WEB+TEXT Vision response."""

    def test_text_wins_for_book_cover(self):
        resp = {
            "responses": [{
                "fullTextAnnotation": {"text": "MAREK KRAJEWSKI\nCZAS ZDRAJCÓW\nznak"},
                "webDetection": {
                    "bestGuessLabels": [{"label": "Marek Krajewski"}],
                },
            }]
        }
        # TEXT gives "MAREK KRAJEWSKI CZAS ZDRAJCÓW" (title+author) — better than author only
        assert _extract_query(resp) == "MAREK KRAJEWSKI CZAS ZDRAJCÓW"

    def test_web_wins_when_no_clean_text(self):
        resp = {
            "responses": [{
                "fullTextAnnotation": {"text": ""},
                "webDetection": {
                    "bestGuessLabels": [{"label": "iphone 15 pro"}],
                },
            }]
        }
        assert _extract_query(resp) == "iphone 15 pro"

    def test_best_guess_label_used_when_text_absent(self):
        resp = {
            "responses": [{
                "webDetection": {
                    "bestGuessLabels": [{"label": "iphone 15 pro"}],
                    "webEntities": [{"description": "Apple", "score": 9.9}],
                }
            }]
        }
        assert _extract_query(resp) == "iphone 15 pro"

    def test_falls_back_to_highest_scoring_entity(self):
        resp = {
            "responses": [{
                "webDetection": {
                    "bestGuessLabels": [],
                    "webEntities": [
                        {"description": "Smartphone", "score": 1.2},
                        {"description": "Sony WH-1000XM5", "score": 8.7},
                        {"description": "Headphones", "score": 4.0},
                    ],
                }
            }]
        }
        assert _extract_query(resp) == "Sony WH-1000XM5"

    def test_skips_blank_labels(self):
        resp = {
            "responses": [{
                "webDetection": {
                    "bestGuessLabels": [{"label": "  "}],
                    "webEntities": [{"description": "Lenovo ThinkPad", "score": 5.0}],
                }
            }]
        }
        assert _extract_query(resp) == "Lenovo ThinkPad"

    @pytest.mark.parametrize("resp", [
        {},
        {"responses": []},
        {"responses": [{}]},
        {"responses": [{"webDetection": {}}]},
        {"responses": [{"webDetection": {"bestGuessLabels": [], "webEntities": []}}]},
    ])
    def test_empty_returns_none(self, resp):
        assert _extract_query(resp) is None


class TestImageToQuery:
    """The async call path, with the HTTP layer mocked."""

    async def test_returns_parsed_query(self, monkeypatch):
        monkeypatch.setattr(image_search, "GOOGLE_VISION_API_KEY", "test-key")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "responses": [{
                        "webDetection": {"bestGuessLabels": [{"label": "lego star wars"}]}
                    }]
                },
            )

        transport = httpx.MockTransport(handler)
        real_client = httpx.AsyncClient

        def make_client(*args, **kwargs):
            kwargs["transport"] = transport
            return real_client(*args, **kwargs)

        monkeypatch.setattr(image_search.httpx, "AsyncClient", make_client)

        assert await image_to_query(b"fake-bytes") == "lego star wars"

    async def test_raises_without_key(self, monkeypatch):
        monkeypatch.setattr(image_search, "GOOGLE_VISION_API_KEY", "")
        with pytest.raises(RuntimeError):
            await image_to_query(b"fake-bytes")
