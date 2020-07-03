from abc import ABC, abstractmethod
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from utils import get_current_timestamp_ms


class BaseAssigner(ABC):

    def __init__(self):
        """
        All assigners have a background task which updates the liveliness of its Snowfall instance in the manifest
        at periodic intervals
        """
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
        The assigner, and by extension its Snowfall instance, is alive iff its generator id is still reserved.
        """
        ms_since_last_updated = current_timestamp_ms - self.last_alive_ms
        if ms_since_last_updated <= self.ms_to_release_generator_id:
            return True
        else:
            return False

    def update_liveliness_job(self):
        self._set_liveliness(
            current_timestamp_ms=get_current_timestamp_ms(),
            generator_id=self.generator_id
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
    def epoch_start_date(self) -> datetime:
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