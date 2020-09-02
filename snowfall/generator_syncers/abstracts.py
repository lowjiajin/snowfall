from abc import ABC, abstractmethod
from apscheduler.schedulers.background import BackgroundScheduler
import logging

from snowfall.utils import get_current_timestamp_ms


class BaseSyncer(ABC):

    PROBE_MISSES_TO_RELEASE = 2
    MAX_GENERATOR_ID = 2 ** 12 - 1

    def __init__(self):
        """
        All syncers have a background task which updates the liveliness of its Snowfall instance in the manifest
        at periodic intervals
        """
        logging.info("Initializing generator syncer base class with liveliness scheduler")
        self._last_alive_ms = 0
        self._generator_id = self._claim_generator_id()

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self.update_liveliness_job,
            trigger="interval",
            seconds=self.liveliness_probe_s,
        )
        self.scheduler.start()

    def is_alive(
            self,
            current_timestamp_ms: int
    ):
        """
        The syncer, and by extension its Snowfall instance, is alive iff its generator id is still reserved.
        """
        ms_since_last_updated = current_timestamp_ms - self._last_alive_ms
        if ms_since_last_updated <= self.ms_to_release_generator_id:
            return True
        else:
            return False

    def update_liveliness_job(self):
        self._set_liveliness(
            current_timestamp_ms=get_current_timestamp_ms(),
            generator_id=self._generator_id
        )

    @property
    @abstractmethod
    def liveliness_probe_s(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def ms_to_release_generator_id(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def generator_id(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def last_alive_ms(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def epoch_start_ms(self) -> int:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def create_schema_group(cls) -> None:
        raise NotImplementedError

    @abstractmethod
    def _claim_generator_id(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def _set_liveliness(
            self,
            current_timestamp_ms: int,
            generator_id: int

    ) -> None:
        raise NotImplementedError
