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
    num_art: int


class SafefeedClient:
    """Asynchronous Safefeed client using aiohttp"""

    key: str
    doc_format: Literal["json"]
    interval: int
    timeout: int
    base_url: str
    num_art: int
    lastid: int | None
    expected_rate: float | None
    _session: aiohttp.ClientSession
    _last_num: int
    _last_request_time: datetime.datetime | None = None
    _autoconfig: bool = True

    def __init__(
        self,
        key: str,
        interval: int | None = None,
        timeout: int = 10,
        lastid: int | None = None,
        base_url: str = "https://feed.opoint.com/safefeed.php",
        num_art: int | None = None,
        expected_rate: float | None = None,
    ) -> None:
        self.key = key
        self.interval = interval if interval is not None else 60
        self.timeout = timeout
        self.base_url = base_url
        self.num_art = num_art if num_art is not None else 500
        self.lastid = lastid
        self.expected_rate = expected_rate
        self._session = aiohttp.ClientSession()
        if interval or num_art:
            self._autoconfig = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return await self._session.close()

    @property
    def is_behind(self) -> bool:
        """Denotes whether the client believes that it is "behind" and currently catching up the the current, based on recent responses."""
        return self._last_num > (self.num_art) * 0.9

    async def _fetch_articles(
        self, lastid: int | None = None, size: int | None = None
    ) -> _BaseRequestContextManager[aiohttp.ClientResponse]:
        now = datetime.datetime.now()
        target = (
            self._last_request_time + datetime.timedelta(seconds=self.interval)
            if self._last_request_time
            else now
        )
        if now < target and not self.is_behind:
            await asyncio.sleep((target - now).total_seconds())

        self._last_request_time = datetime.datetime.now()

        return self._session.get(
            self.base_url,
            params={
                "key": self.key,
                "doc_format": "json",
                "lastid": i if (i := lastid or self.lastid) is not None else "?",
                "num_art": size or self.num_art,
            },
            timeout=aiohttp.ClientTimeout(total=self.timeout),
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
                self.expected_rate = self.expected_rate or data["searchresult"].get(
                    "expected_rate"
                )
                if self.expected_rate and self._autoconfig:
                    logging.debug("Configuring parameters")
                    self.interval = 70 / self.expected_rate**0.5
                    self.num_art = 100 * self.expected_rate**0.5

                logging.debug(
                    f"expected_rate: {self.expected_rate}, interval: {self.interval}, num_art: {self.num_art}"
                )
            except KeyError:
                logging.warn(
                    "Could not update internal state. JSON response is probably malformed somehow."
                )

            return data

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
