from typing import Type
from datetime import datetime
from time import sleep

from generator_syncers.abstracts import BaseSyncer
from generator_syncers.simple_syncer import SimpleSyncer
from utils import get_current_timestamp_ms


class Snowfall:

    MAX_MS_SINCE_EPOCH = 2 ** 41 - 1
    MAX_LOOPING_COUNT = 2 ** 11 - 1

    def __init__(
            self,
            generator_syncer_type: Type[BaseSyncer] = SimpleSyncer,
            **kwargs
    ):
        """
        A Snowfall object that generates GUIDs.
        :param generator_syncer_type: Specify a IDSyncer class. An IDSyncer instance will be created to coordinate
                                 the generator_id and epoch_start across multiple Snowfall instances.
        """
        self.generator_syncer = generator_syncer_type(**kwargs)
        self.generator_id = self.generator_syncer.generator_id
        self.EPOCH_START_MS = int(self.generator_syncer.epoch_start_date.timestamp() * 1000)
        self.looping_counter = 0
        self.guid_last_generated_at = self.EPOCH_START_MS

    def get_guid(self) -> int:
        """
        :return: A valid Snowfall GUID
        """
        ms_since_epoch = self._get_ms_since_epoch()
        self._increment_looping_count(ms_since_epoch=ms_since_epoch)
        guid = self._combine_into_guid(ms_since_epoch=ms_since_epoch)
        return guid

    def _get_ms_since_epoch(self) -> int:
        """
        41 bit integer representing the number of ms since a user-definable epoch start.
        """
        current_timestamp_ms = get_current_timestamp_ms()
        ms_since_epoch = current_timestamp_ms - self.EPOCH_START_MS

        if not self.generator_syncer.is_alive(current_timestamp_ms=current_timestamp_ms):
            raise RuntimeError("Generator ID no longer reserved by this instance.")
        elif ms_since_epoch > self.MAX_MS_SINCE_EPOCH:
            raise OverflowError(f"ms_since_epoch: {ms_since_epoch}, it has been >2^41ms since epoch_start")

        return ms_since_epoch

    def _increment_looping_count(
            self,
            ms_since_epoch: int
    ) -> int:
        """
        An auto-incrementing count that loops within the range [0, 2048). If the count >= 2048 within a single ms,
        throttle the output until the next ms to ensure GUID stays unique.
        """
        if self.guid_last_generated_at != ms_since_epoch:
            self.looping_counter = 0
        else:
            if self.looping_counter > self.MAX_LOOPING_COUNT:
                s_until_next_ms = (ms_since_epoch + 1) / 1000 - datetime.utcnow().timestamp()
                sleep(secs=max(s_until_next_ms, 0))
            self.looping_counter += 1
        return self.looping_counter

    def _combine_into_guid(
            self,
            ms_since_epoch: int
    ) -> int:
        """
        Combines the ms_since_epoch, looping_count, and generator_id according to the Snowfall GUID spec.
        """
        ms_since_epoch_part = ms_since_epoch << 23
        looping_count_part = self.looping_counter << 12
        guid = ms_since_epoch_part + looping_count_part + self.generator_id
        self.guid_last_generated_at = ms_since_epoch
        return guid


SimpleSyncer.create_schema_group(schema_group_name="foo")
generator_1 = Snowfall(generator_syncer_type=SimpleSyncer, schema_group_name="foo")
generator_2 = Snowfall(generator_syncer_type=SimpleSyncer, schema_group_name="foo")
print(generator_1.generator_id, generator_2.generator_id)

for x in range(10):
    print(f"Generator 1: {generator_1.get_guid()}")
    print(f"Generator 2: {generator_2.get_guid()}")
    sleep(1)
