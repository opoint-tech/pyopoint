from typing import Any, Coroutine, Literal, TypedDict, Self
import aiohttp
import asyncio


class SafefeedOptions(TypedDict, total=False):
    doc_format: Literal["json"] | Literal["xml"]
    interval: int
    timeout: int
    base_url: str
    batch_size: int

class Article(TypedDict):
    pass


class OpointSafefeedClient:
    key: str
    doc_format: Literal["json"] | Literal["xml"]
    interval: int
    timeout: int
    base_url: str
    batch_size: int
    position: tuple[int, int]
    _session: aiohttp.ClientSession

    def __init__(
        self,
        key: str,
        doc_format: Literal["json"] | Literal["xml"] = "json",
        interval: int = 10,
        timeout: int = 5,
        base_url: str = "https://feed.opoint.com/safefeed.php",
        batch_size: int = 500
    ) -> None:
        self.key = key
        self.interval = interval
        self.doc_format = doc_format
        self.timeout = timeout
        self.base_url = base_url
        self.batch_size = batch_size
        self._session = aiohttp.ClientSession()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return await self._session.close()

    async def get_articles(self, start_id: tuple[int, int] | None = None, size: int | None = None) -> list[Article]:
        return []


async def amain() -> list[Article]:
    async with OpointSafefeedClient('sample-token') as client:
        return(await client.get_articles())

def main() -> None:
    print(asyncio.run(amain()))

if __name__ == '__main__':
    main()
