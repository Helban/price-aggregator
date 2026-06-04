import asyncio
import base64
import json
import time
import webbrowser
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import httpx

from config import ALLEGRO_CLIENT_ID, ALLEGRO_CLIENT_SECRET
from models import Product
from scrapers.base import ScraperBase

_AUTH_URL = "https://allegro.pl/auth/oauth/token"
_DEVICE_URL = "https://allegro.pl/auth/oauth/device"
_API_BASE = "https://api.allegro.pl"
_ACCEPT = "application/vnd.allegro.public.v1+json"
_TOKEN_FILE = Path(__file__).parent.parent / ".allegro_token.json"


class AllegroScraper(ScraperBase):
    source_name = "Allegro"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)

    # ------------------------------------------------------------------ auth

    def _basic_auth(self) -> str:
        return base64.b64encode(
            f"{ALLEGRO_CLIENT_ID}:{ALLEGRO_CLIENT_SECRET}".encode()
        ).decode()

    def _load_token(self) -> Optional[dict]:
        if _TOKEN_FILE.exists():
            return json.loads(_TOKEN_FILE.read_text())
        return None

    def _save_token(self, data: dict) -> None:
        data["saved_at"] = time.time()
        _TOKEN_FILE.write_text(json.dumps(data))

    async def _refresh(self, refresh_token: str) -> dict:
        resp = await self._client.post(
            _AUTH_URL,
            params={"grant_type": "refresh_token", "refresh_token": refresh_token},
            headers={"Authorization": f"Basic {self._basic_auth()}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def _device_flow(self) -> dict:
        resp = await self._client.post(
            _DEVICE_URL,
            data={"client_id": ALLEGRO_CLIENT_ID},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        info = resp.json()

        url = info.get("verification_uri_complete", info["verification_uri"])
        interval = info.get("interval", 5)

        print(f"\nOtwórz w przeglądarce i zatwierdź dostęp:\n  {url}\n")
        webbrowser.open(url)
        print("Czekam na potwierdzenie...", flush=True)

        while True:
            await asyncio.sleep(interval)
            resp = await self._client.post(
                _AUTH_URL,
                params={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": info["device_code"],
                },
                headers={"Authorization": f"Basic {self._basic_auth()}"},
            )
            if resp.status_code == 400:
                err = resp.json().get("error", "")
                if err == "authorization_pending":
                    continue
                if err == "slow_down":
                    interval += 5
                    continue
                raise RuntimeError(f"Allegro device flow: {resp.text}")
            resp.raise_for_status()
            return resp.json()

    async def _get_token(self) -> str:
        if not ALLEGRO_CLIENT_ID or not ALLEGRO_CLIENT_SECRET:
            raise RuntimeError(
                "ALLEGRO_CLIENT_ID / ALLEGRO_CLIENT_SECRET not set. "
                "Copy .env.example → .env and fill in your API credentials."
            )

        cached = self._load_token()

        if cached:
            age = time.time() - cached.get("saved_at", 0)
            expires_in = cached.get("expires_in", 43200)
            if age < expires_in - 60:
                return cached["access_token"]

            # token wygasł — odśwież
            if "refresh_token" in cached:
                try:
                    token_data = await self._refresh(cached["refresh_token"])
                    self._save_token(token_data)
                    return token_data["access_token"]
                except httpx.HTTPStatusError:
                    pass  # refresh się nie udał, wróć do device flow

        token_data = await self._device_flow()
        self._save_token(token_data)
        print("Autoryzacja zakończona.\n")
        return token_data["access_token"]

    # ------------------------------------------------------------------ search

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
        if not resp.is_success:
            raise RuntimeError(f"Allegro API {resp.status_code}: {resp.text[:500]}")

        items = resp.json().get("items", {})
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
