"""Image -> search query bridge using the Google Cloud Vision REST API.

None of the target marketplaces support native reverse-image search, so we turn
an image into a text query and feed it into the normal pipeline.
We call the REST endpoint with httpx directly instead of the google-cloud-vision
SDK: one less heavy dependency, and a plain API key is simpler to set up than a
service-account JSON file.

One request sends two features simultaneously:
  WEB_DETECTION  — good for branded products, electronics (returns a ready phrase)
  TEXT_DETECTION — good for book covers, packaging with visible text
The picker tries text first when it looks like a clean product name (2-6 words),
otherwise falls back to the web-detection result.
"""
import base64
import re

import httpx

from config import GOOGLE_VISION_API_KEY

_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"

# Noise tokens that appear on book covers / packaging but are not product names.
_NOISE = {"znak", "pwn", "helion", "allegro", "empik", "isbn", "www"}


def _pick_from_text(full_text: str) -> str | None:
    """Extract a usable product name from raw TEXT_DETECTION output.

    TEXT_DETECTION puts each word on its own line when text is large (e.g. book
    covers). We therefore collect words — not lines — until we have 6, so that
    "znak\nMAREK\nKRAJEWSKI\nCZAS\nZDRAJCÓW" becomes "MAREK KRAJEWSKI CZAS
    ZDRAJCÓW" rather than being cut off at 3 lines / 2 usable words.
    """
    if not full_text:
        return None

    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    # Collect up to 6 words from the top of the image (title/brand area).
    words: list[str] = []
    for line in lines:
        words.extend(line.split())
        if len(words) >= 6:
            break

    # Drop known noise tokens, cap at 6.
    words = [w for w in words[:6] if w.lower() not in _NOISE]
    candidate = " ".join(words).strip()

    word_count = len(candidate.split())
    if 2 <= word_count <= 6:
        return candidate

    return None


def _extract_query(vision_response: dict) -> str | None:
    """Pick the best search query from a combined WEB+TEXT Vision response.

    Priority:
      1. TEXT_DETECTION first 3 lines — wins for books/packaging with clear text
      2. WEB_DETECTION bestGuessLabels — wins for branded electronics/products
      3. WEB_DETECTION webEntities (highest score)
      4. None → UI asks the user to type manually
    """
    responses = vision_response.get("responses") or []
    if not responses:
        return None
    r = responses[0]

    # --- TEXT path ---
    full_text = (r.get("fullTextAnnotation") or {}).get("text") or ""
    text_candidate = _pick_from_text(full_text)

    # --- WEB path ---
    web = r.get("webDetection") or {}
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

    # --- Decision ---
    # Prefer text when it produced something clean; web otherwise.
    return text_candidate or web_candidate or None


async def image_to_query(image_bytes: bytes) -> str | None:
    """Resolve a search query from raw image bytes via Google Vision.

    Returns the detected product phrase, or None when Vision finds nothing
    usable. Raises RuntimeError if the API key is missing.
    """
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
