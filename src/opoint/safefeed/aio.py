import asyncio
import json
import logging
from typing import Any, Literal, Self, TypedDict, cast

import aiohttp

from opoint.safefeed.api import FeedResponse


class SafefeedOptions(TypedDict, total=False):
    doc_format: Literal["json"] | Literal["xml"]
    interval: int
    timeout: int
    base_url: str
    batch_size: int


class SafefeedClient:
    """Asynchronous Safefeed client using aiohttp"""

    key: str
    doc_format: Literal["json"] | Literal["xml"]
    interval: int
    timeout: int
    base_url: str
    batch_size: int
    lastid: int
    _session: aiohttp.ClientSession

    def __init__(
        self,
        key: str,
        doc_format: Literal["json"] | Literal["xml"] = "json",
        interval: int = 10,
        timeout: int = 5,
        base_url: str = "https://feed.opoint.com/safefeed.php",
        batch_size: int = 500,
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

    async def _fetch_articles(
        self, lastid: int | None = None, size: int | None = None
    ) -> aiohttp.ClientResponse:
        async with await self._session.get(
            self.base_url,
            params={
                "key": self.key,
                "doc_format": self.doc_format,
                "lastid": lastid or self.lastid,
                "num_art": size or self.batch_size,
            },
        ) as response:
            logging.info(response.status)
            return response

    async def get_articles_json(self) -> FeedResponse:
        response = await self._fetch_articles()
        data: FeedResponse
        try:
            data = cast(FeedResponse, await response.json())
        except aiohttp.ContentTypeError:
            logging.error("Content-Type is not 'application/json'")
        except UnicodeDecodeError:
            logging.error("Could not decode Unicode data. This is very bad!")
        except json.JSONDecodeError as e:
            logging.error("Could not decode JSON response body.", e)
            logging.debug("Full response body follows:")
            logging.debug(await response.text())

        self.lastid = data["searchresult"]["document"][-1]["id_delivery"]

        return data

    async def get_articles_xml(self) -> str:
        return await (await self._fetch_articles()).text()

    async def seek(self, timestamp: int) -> int:
        return 0


async def main() -> None:
    async with SafefeedClient("sample-token") as client:
        print(await client._fetch_articles())


if __name__ == "__main__":
    asyncio.run(main())
