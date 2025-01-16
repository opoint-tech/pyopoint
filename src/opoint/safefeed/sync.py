import datetime
import json
import logging
import time
from typing import Literal, cast, Self

import requests

from opoint.safefeed.api import FeedResponse


class SyncSafefeedClient:
    key: str
    doc_format: Literal["json"] | Literal["xml"]
    interval: int
    timeout: int
    base_url: str
    batch_size: int
    lastid: int | None
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

    def _fetch_articles(
        self, lastid: int | None = None, size: int | None = None
    ) -> requests.Response:
        now = datetime.datetime.now()
        target = self._last_request_time + datetime.timedelta(seconds=self.interval) if self._last_request_time else now
        if now < target and self._last_num < 0.9 * self.batch_size:
            time.sleep((target - now).total_seconds())

        self._last_request_time = datetime.datetime.now()

        params: dict[str, str | int] = {
            "key": self.key,
            "doc_format": self.doc_format,
            "lastid": i if (i := lastid or self.lastid) is not None else '?',
            "num_art": size or self.batch_size,
        }

        return requests.get(
            self.base_url,
            params=params,
        )

    def get_articles_json(
        self, lastid: int | None = None, size: int | None = None
    ) -> FeedResponse | None:
        """Get the next batch of articles"""
        response = self._fetch_articles(lastid, size)
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
        except KeyError:
            logging.warn(
                "Could not update internal state. JSON response is probably malformed somehow."
            )

        return data

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> FeedResponse | None:
        return self.get_articles_json()

    def get_articles_xml(self) -> str:
        return self._fetch_articles().text
