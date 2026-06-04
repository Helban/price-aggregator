import base64
import time
from decimal import Decimal
from typing import List, Optional

import httpx

from config import ALLEGRO_CLIENT_ID, ALLEGRO_CLIENT_SECRET
from models import Product
from scrapers.base import ScraperBase

_AUTH_URL = "https://allegro.pl/auth/oauth/token"
_API_BASE = "https://api.allegro.pl"
_ACCEPT = "application/vnd.allegro.public.v1+json"


class AllegroScraper(ScraperBase):
    source_name = "Allegro"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        if not ALLEGRO_CLIENT_ID or not ALLEGRO_CLIENT_SECRET:
            raise RuntimeError(
                "ALLEGRO_CLIENT_ID / ALLEGRO_CLIENT_SECRET not set. "
                "Copy .env.example → .env and fill in your API credentials."
            )

        credentials = base64.b64encode(
            f"{ALLEGRO_CLIENT_ID}:{ALLEGRO_CLIENT_SECRET}".encode()
        ).decode()

        resp = await self._client.post(
            _AUTH_URL,
            params={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {credentials}"},
        )
        resp.raise_for_status()
        data = resp.json()

        self._token = data["access_token"]
        self._token_expires_at = time.monotonic() + data.get("expires_in", 3600) - 60
        return self._token

    async def search(self, query: str, limit: int = 20) -> List[Product]:
        token = await self._get_token()

        resp = await self._client.get(
            f"{_API_BASE}/offers/listing",
            params={"phrase": query, "limit": limit, "sort": "+price"},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": _ACCEPT,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", {})
        raw = items.get("regular", []) + items.get("promoted", [])
        return [self._parse_item(item) for item in raw[:limit]]

    def _parse_item(self, item: dict) -> Product:
        images = item.get("images", [])
        shipping_raw = (
            item.get("delivery", {})
            .get("lowestAndDefaultDeliveryMethodPrice", {})
        )
        return Product(
            name=item["name"],
            price=Decimal(str(item["price"]["amount"])),
            url=f"https://allegro.pl/oferta/{item['id']}",
            source=self.source_name,
            image_url=images[0]["url"] if images else None,
            condition=item.get("condition"),
            seller=item.get("seller", {}).get("login"),
            shipping_price=Decimal(str(shipping_raw["amount"])) if shipping_raw else None,
        )

    async def close(self) -> None:
        await self._client.aclose()
