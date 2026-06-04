from abc import ABC, abstractmethod
from typing import List

from models import Product


class ScraperBase(ABC):
    source_name: str = ""

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[Product]:
        ...

    async def close(self) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
