from typing import TypeVar
from dataclasses import dataclass


T = TypeVar("T")


@dataclass
class FeedConfigValue[T]:
    value: T
    autoconfig: bool


class FeedConfiguration:
    interval: FeedConfigValue[int]
    num_art: FeedConfigValue[int]
    expected_rate: FeedConfigValue[float]

    def __init__(
        self,
        interval: int | None = None,
        num_art: int | None = None,
        expected_rate: float | None = None,
    ) -> None:
        self.interval = FeedConfigValue(
            value=interval or 10, autoconfig=interval is None
        )
        self.num_art = FeedConfigValue(value=num_art or 500, autoconfig=num_art is None)
        self.expected_rate = FeedConfigValue(
            value=expected_rate or 50, autoconfig=expected_rate is None
        )

    def update(self, num_received: int) -> None:
        if self.expected_rate.autoconfig:
            self.expected_rate.value = 0.9 * self.expected_rate.value + 0.1 * (
                num_received / self.interval.value
            )

        if self.interval.autoconfig and self.num_art.autoconfig:
            self.interval.value = min(60 / self.expected_rate.value**0.5, 900)
            self.num_art.value = max(120 * self.expected_rate.value**0.5, 50.0)
        else:
            if self.interval.autoconfig:
                self.interval.value = int(
                    (self.num_art.value / self.expected_rate.value) // 2
                )
            if self.num_art.autoconfig:
                self.num_art.value = int(
                    2 * (self.expected_rate.value * self.interval.value)
                )
