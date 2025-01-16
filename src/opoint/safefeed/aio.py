import asyncio
import json
import logging
import datetime
from typing import Any, Literal, Self, TypedDict, cast

import aiohttp
from aiohttp.client import _BaseRequestContextManager

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
    lastid: int | None
    _session: aiohttp.ClientSession
    _last_num: int
    _last_request_time: datetime.datetime | None = None

    def __init__(
        self,
        key: str,
        doc_format: Literal["json"] | Literal["xml"] = "json",
        interval: int = 10,
        timeout: int = 5,
        lastid: int | None = None,
        base_url: str = "https://feed.opoint.com/safefeed.php",
        batch_size: int = 500,
    ) -> None:
        self.key = key
        self.interval = interval
        self.doc_format = doc_format
        self.timeout = timeout
        self.base_url = base_url
        self.batch_size = batch_size
        self.lastid = lastid
        self._session = aiohttp.ClientSession()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return await self._session.close()

    async def _fetch_articles(
        self, lastid: int | None = None, size: int | None = None
    ) -> _BaseRequestContextManager[aiohttp.ClientResponse]:
        now = datetime.datetime.now()
        target = self._last_request_time + datetime.timedelta(seconds=self.interval) if self._last_request_time else now
        if now < target and self._last_num < 0.9 * self.batch_size:
            await asyncio.sleep((target - now).total_seconds())

        self._last_request_time = datetime.datetime.now()

        return self._session.get(
            self.base_url,
            params={
                "key": self.key,
                "doc_format": self.doc_format,
                "lastid": i if (i := lastid or self.lastid) is not None else '?',
                "num_art": size or self.batch_size,
            },
        )

    async def get_articles(
        self, lastid: int | None = None, size: int | None = None
    ) -> FeedResponse | None:
        """Get the next batch of articles"""
        async with await self._fetch_articles(lastid, size) as response:
            data: FeedResponse
            try:
                # TODO: Check HTTP status codes and stuff
                data = cast(FeedResponse, await response.json())
            except aiohttp.ContentTypeError:
                logging.error("Content-Type is not 'application/json'")
                return None
            except UnicodeDecodeError:
                logging.error("Could not decode Unicode data. This is very bad!")
                return None
            except json.JSONDecodeError as e:
                logging.error("Could not decode JSON response body.", e)
                logging.debug("Full response body follows:")
                logging.debug(await response.text())
                return None

            try:
                self.lastid = data["searchresult"]["search_start"]
                self._last_num = data["searchresult"].get("documents", 0)
            except KeyError:
                logging.warn(
                    "Could not update internal state. JSON response is probably malformed somehow."
                )

            return data

    async def get_articles_xml(self) -> str:
        async with await self._fetch_articles() as response:
            return await response.text()

    # async def seek(self, timestamp: int) -> int:
    #     return 0

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> FeedResponse | None:
        return await self.get_articles()


async def main() -> None:
    async with SafefeedClient("sample-token") as client:
        print(await client._fetch_articles())


if __name__ == "__main__":
    asyncio.run(main())
