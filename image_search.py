import base64

import httpx

from config import GOOGLE_VISION_API_KEY

_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"

# Noise tokens that appear on book covers / packaging but are not product names.
_NOISE = {"znak", "pwn", "helion", "allegro", "empik", "isbn", "www"}


def _pick_from_text(full_text: str) -> str | None:
    """TEXT_DETECTION puts each word on its own line for large text (book covers).
    We collect words — not lines — so "znak\\nMAREK\\nKRAJEWSKI\\nCZAS\\nZDRAJCÓW"
    becomes "MAREK KRAJEWSKI CZAS ZDRAJCÓW" instead of being cut at 3 lines.
    """
    if not full_text:
        return None

    lines = [line.strip() for line in full_text.splitlines() if line.strip()]

    words: list[str] = []
    for line in lines:
        words.extend(line.split())
        if len(words) >= 6:
            break

    words = [w for w in words[:6] if w.lower() not in _NOISE]
    candidate = " ".join(words).strip()

    word_count = len(candidate.split())
    if 2 <= word_count <= 6:
        return candidate

    return None


def _extract_query(vision_response: dict) -> str | None:
    """Picks the best query from a combined WEB+TEXT Vision response.

    Priority:
      1. TEXT_DETECTION — wins for books/packaging with clear text
      2. WEB_DETECTION bestGuessLabels — wins for branded electronics
      3. WEB_DETECTION webEntities (highest score)
      4. None — UI asks user to type manually
    """
    responses = vision_response.get("responses") or []
    if not responses:
        return None
    detection = responses[0]

    full_text = (detection.get("fullTextAnnotation") or {}).get("text") or ""
    text_candidate = _pick_from_text(full_text)

    web = detection.get("webDetection") or {}
    web_candidate = None
    for label in web.get("bestGuessLabels") or []:
        t = (label.get("label") or "").strip()
        if t:
            web_candidate = t
            break
    if not web_candidate:
        entities = [
            e for e in (web.get("webEntities") or [])
            if (e.get("description") or "").strip()
        ]
        if entities:
            entities.sort(key=lambda e: e.get("score", 0), reverse=True)
            web_candidate = entities[0]["description"].strip()

    return text_candidate or web_candidate or None


async def image_to_query(image_bytes: bytes) -> str | None:
    if not GOOGLE_VISION_API_KEY:
        raise RuntimeError(
            "GOOGLE_VISION_API_KEY is not set — see .env.example for setup."
        )

    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                "features": [
                    {"type": "WEB_DETECTION"},
                    {"type": "DOCUMENT_TEXT_DETECTION"},
                ],
            }
        ]
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _VISION_URL,
            params={"key": GOOGLE_VISION_API_KEY},
            json=payload,
        )
        resp.raise_for_status()
        return _extract_query(resp.json())
