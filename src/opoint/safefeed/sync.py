import datetime
import json
import logging
import time
from typing import Any, Literal, Self, TypedDict, cast

import requests

from opoint.safefeed.api import FeedResponse


class SafefeedOptions(TypedDict, total=False):
    doc_format: Literal["json"] | Literal["xml"]
    interval: int
    timeout: int
    base_url: str
    num_art: int


class SyncSafefeedClient:
    """
    Synchronous Safefeed client using requests.

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
    interval: int
    timeout: int
    base_url: str
    num_art: int
    lastid: int | None
    expected_rate: float | None
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
    ) -> None:
        self.key = key
        self.interval = interval if interval is not None else 60
        self.timeout = timeout
        self.base_url = base_url
        self.num_art = num_art if num_art is not None else 500
        self.lastid = lastid
        self.expected_rate = expected_rate
        if interval or num_art or expected_rate:
            self._autoconfig = False

    @property
    def is_behind(self) -> bool:
        """Denotes whether the client believes that it is "behind" and currently catching up the the current, based on recent responses."""
        return self._last_num > (self.num_art) * 0.95

    def get_articles(
        self, lastid: int | None = None, size: int | None = None
    ) -> FeedResponse | None:
        """Get the next batch of articles"""
        now = datetime.datetime.now()
        target = (
            self._last_request_time + datetime.timedelta(seconds=self.interval)
            if self._last_request_time
            else now
        )
        if now < target and not self.is_behind:
            logging.info(
                f"Sleeping {(target - now).total_seconds()} seconds to respect interval setting"
            )
            time.sleep((target - now).total_seconds())
            logging.info("Proceeding")

        self._last_request_time = datetime.datetime.now()

        response = requests.get(
            self.base_url,
            params={
                "key": self.key,
                "doc_format": "json",
                "lastid": i if (i := lastid or self.lastid) is not None else "?",
                "num_art": size or self.num_art,
            },
            timeout=self.timeout,
        )
        data: FeedResponse
        try:
            # TODO: Check HTTP status codes and stuff
            data = cast(FeedResponse, response.json())
        except UnicodeDecodeError:
            logging.error("Could not decode Unicode data. This is very bad!")
            return None
        except json.JSONDecodeError as e:
            logging.error("Could not decode JSON response body.", e)
            logging.debug("Full response body follows:")
            logging.debug(response.text)
            return None

        try:
            self.lastid = data["searchresult"]["search_start"]
            self._last_num = data["searchresult"].get("documents", 0)
            logging.debug(f"Got {data['searchresult']['documents']} articles")
            if self._autoconfig and not self.is_behind:
                logging.debug("Configuring parameters")
                self.expected_rate = 0.9 * (self.expected_rate or 40) + 0.1 * (
                    data["searchresult"].get("expected_rate")
                    or (
                        data["searchresult"]["documents"]
                        and (data["searchresult"]["documents"] / self.interval)
                        or self.expected_rate
                        or 40
                    )
                )
                self.interval = min(60 / self.expected_rate**0.5, 900)
                self.num_art = max(120 * self.expected_rate**0.5, 50.0)

            if not self.is_behind:
                logging.debug(
                    f"expected_rate: {(self.expected_rate or 0)}/s, interval: {self.interval}, num_art: {self.num_art}"
                )
            else:
                logging.debug(
                    "Is behind, cannot estimate rate or configure interval/num_art"
                )
        except KeyError:
            logging.warn(
                "Could not update internal state. JSON response is probably malformed somehow."
            )

        return data

    # async def seek(self, timestamp: int) -> int:
    #     return 0

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> FeedResponse | None:
        return self.get_articles()


def main() -> None:
    with SyncSafefeedClient("sample-token") as client:
        print(client.get_articles())


if __name__ == "__main__":
    main()
