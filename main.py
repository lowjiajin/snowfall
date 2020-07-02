from typing import Optional, Union
from datetime import datetime
from time import sleep

from id_assigners.abstracts import AbstractAssigner


class Snowfall:

    MAX_MS_SINCE_EPOCH = 2 ** 40 - 1
    MAX_LOOPING_COUNT = 2 ** 11 - 1
    MAX_GENERATOR_ID = 2 ** 12 - 1

    def __init__(
            self,
            generator_id: Optional[int] = None,
            epoch_start: Union[datetime] = datetime(2020, 1, 1),
            id_assigner: Optional[AbstractAssigner] = None
    ):
        """
        A Snowfall object that generates GUIDs.
        :param generator_id: A number between [0, 4096) that uniquely identifies this Snowfall instance.
        :param epoch_start: GUIDs are unique for up to 2^40ms (~70 years) from the epoch start.
        :param id_assigner: An IDAssigner to help coordinate the generator_id and epoch_start across multiple
                            Snowfall instances.
        """

        if id_assigner is None:
            self.generator_id = generator_id
            self.epoch_start = epoch_start
        else:
            self.generator_id = id_assigner.claim_generator_id()
            self.epoch_start = id_assigner.get_epoch_start()

        if self.generator_id > self.MAX_GENERATOR_ID:
            raise ValueError(f"generator_id: {generator_id} cannot be >= 4096")
        elif self.epoch_start > datetime.utcnow():
            raise ValueError(f"epoch_start: {epoch_start} cannot be in the future of the current UTC time")

        self.epoch_start = int(self.epoch_start.timestamp() * 1000)
        self.looping_counter = 0
        self.guid_last_generated_at = self.epoch_start

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
        40 bit integer representing the number of ms since a user-definable epoch start.
        """
        current_unix_timestamp = int(datetime.utcnow().timestamp() * 1000)
        ms_since_epoch = current_unix_timestamp - self.epoch_start

        if ms_since_epoch > self.MAX_MS_SINCE_EPOCH:
            raise OverflowError(f"ms_since_epoch: {ms_since_epoch}, it has been >2^40ms since epoch_start")

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
                s_until_next_ms = (ms_since_epoch + 1) / 1000 - datetime.now().timestamp()
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
