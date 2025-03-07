import asyncio
import json
import logging
import datetime
from typing import Any, Literal, Self, TypedDict, cast

import aiohttp

from opoint.safefeed.api import FeedResponse
from opoint.safefeed.common import FeedConfiguration

logger: logging.Logger = logging.getLogger(__name__)


class SafefeedOptions(TypedDict, total=False):
    doc_format: Literal["json"] | Literal["xml"]
    interval: int
    timeout: int
    base_url: str
    num_art: int


class SafefeedClient:
    """
    Asynchronous Safefeed client using aiohttp.

    By default, will adjust interval and num_art to attempt
    to get relatively consistent batches at consistent intervals.

    If configured with expected_rate, will use that to set
    interval and num_art statically.

    :int interval: interval at which to start requests. Ignored when fallen behind. Keep as None unless you have reason to change it.
    :int timeout: request timeout.
    :int lastid: lastid parameter obtained from a previous request. 0 to start from the oldest article still in the feed, None to start at the current newest.
    :str base_url: the feed base url.
    :int num_art: number of articles to request each time. Only change if you have limitations in processing.
    :float expected_rate: expected rate of articles per second. Keep as None unless you have reason to change it.
    """

    key: str
    doc_format: Literal["json"]
    config: FeedConfiguration
    timeout: int
    base_url: str
    lastid: int | None
    _session: aiohttp.ClientSession
    _last_num: int
    _last_request_time: datetime.datetime | None = None
    _autoconfig: bool = True

    def __init__(
        self,
        key: str,
        interval: int | None = None,
        timeout: int = 30,
        lastid: int | None = None,
        base_url: str = "https://feed.opoint.com/safefeed.php",
        num_art: int | None = None,
        expected_rate: float | None = None,
        log_level: int = logging.ERROR,
    ) -> None:
        global logger
        self.key = key
        self.timeout = timeout
        self.base_url = base_url
        self.lastid = lastid
        self._session = aiohttp.ClientSession()
        self.config = FeedConfiguration(
            interval=interval, num_art=num_art, expected_rate=expected_rate
        )
        logger.setLevel(log_level)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return await self._session.close()

    @property
    def is_behind(self) -> bool:
        """Denotes whether the client believes that it is "behind" and currently catching up the the current, based on recent responses."""
        return self._last_num > (self.config.num_art.value) * 0.95

    async def get_articles(
        self, lastid: int | None = None, size: int | None = None
    ) -> FeedResponse | None:
        """Get the next batch of articles"""
        now = datetime.datetime.now()
        target = (
            self._last_request_time
            + datetime.timedelta(seconds=self.config.interval.value)
            if self._last_request_time
            else now
        )
        if now < target and not self.is_behind:
            logger.info(
                f"Sleeping {(target - now).total_seconds()} seconds to respect interval setting"
            )
            await asyncio.sleep((target - now).total_seconds())
            logger.info("Proceeding")

        self._last_request_time = datetime.datetime.now()

        async with self._session.get(
            self.base_url,
            params={
                "key": self.key,
                "doc_format": "json",
                "lastid": i if (i := lastid or self.lastid) is not None else "?",
                "num_art": size or self.config.num_art.value,
            },
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        ) as response:
            data: FeedResponse
            try:
                # TODO: Check HTTP status codes and stuff
                data = cast(FeedResponse, await response.json())
            except aiohttp.ContentTypeError:
                logger.error("Content-Type is not 'application/json'")
                return None
            except UnicodeDecodeError:
                logger.error("Could not decode Unicode data. This is very bad!")
                return None
            except json.JSONDecodeError as e:
                logger.error("Could not decode JSON response body.", e)
                logger.debug("Full response body follows:")
                logger.debug(await response.text())
                return None

            try:
                self.lastid = data["searchresult"]["search_start"]
                self._last_num = data["searchresult"].get("documents", 0)
                logger.debug(f"Got {data['searchresult']['documents']} articles")
                logger.debug("Configuring parameters")
                self.config.update(self._last_num)

                if not self.is_behind:
                    logger.debug(
                        f"expected_rate: {(self.config.expected_rate.value)}/s, interval: {self.config.interval.value}, num_art: {self.config.num_art.value}"
                    )
                else:
                    logger.debug(
                        "Is behind, cannot estimate rate or configure interval/num_art"
                    )
            except KeyError:
                logger.warn(
                    "Could not update internal state. JSON response is probably malformed somehow."
                )

            return data

    # async def seek(self, timestamp: int) -> int:
    #     return 0

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> FeedResponse | None:
        return await self.get_articles()
