from datetime import datetime
from collections import namedtuple
import numpy as np

from snowfall.generator_syncers.abstracts import BaseSyncer
from snowfall.utils import get_current_timestamp_ms


SchemaGroup = namedtuple(
        typename="SchemaGroup",
        field_names=("liveliness_probe_s", "epoch_start_ms", "manifest")
)


class SimpleSyncer(BaseSyncer):

    schema_groups = dict()

    def __init__(
            self,
            schema_group_name: str = "default"
    ):
        """
        A SimpleSyncer instance that reserves a generator_id for its associated Snowfall instance.
        :param schema_group_name: The schema group we want to associate this SimpleSyncer with.
        """
        schema_group = self.schema_groups.get(schema_group_name)

        if schema_group is None:
            raise KeyError(f"No such schema group found: {schema_group_name}. Call `create_schema_group` first.")
        self._manifest = schema_group.manifest

        self._liveliness_probe_s = schema_group.liveliness_probe_s
        self._ms_to_release_generator_id = self._liveliness_probe_s * 1000 * self.PROBE_MISSES_TO_RELEASE
        self._epoch_start_ms = schema_group.epoch_start_ms
        super().__init__()

    @property
    def liveliness_probe_s(self) -> int:
        return self._liveliness_probe_s

    @property
    def ms_to_release_generator_id(self) -> int:
        return self._ms_to_release_generator_id

    @property
    def generator_id(self) -> int:
        return self._generator_id

    @property
    def last_alive_ms(self) -> int:
        return self._last_alive_ms

    @property
    def epoch_start_ms(self) -> int:
        return self._epoch_start_ms

    @classmethod
    def create_schema_group(
            cls,
            schema_group_name: str = "default",
            liveliness_probe_s: int = 5,
            epoch_start_date: datetime = datetime(2020, 1, 1)
    ) -> None:
        """
        Adds a schema group object to the class
        :param schema_group_name:  Unique name that identifies the schema group.
        :param liveliness_probe_s: Frequency with which the SimpleSyncer instances update their liveliness
                                    in the manifest.
        :param epoch_start_date:   GUIDs are unique for up to 2^41ms (~70 years) from the epoch start date.
        """
        if epoch_start_date > datetime.utcnow():
            raise ValueError(f"epoch_start_date: {epoch_start_date} cannot be in the future of the current UTC time.")

        if schema_group_name in cls.schema_groups:
            raise ValueError(f"schema_group_name: {schema_group_name} already exists.")
        else:
            manifest = np.zeros(
                shape=(cls.MAX_GENERATOR_ID + 1),
                dtype=int
            )
            cls.schema_groups[schema_group_name] = SchemaGroup(
                liveliness_probe_s=liveliness_probe_s,
                epoch_start_ms=epoch_start_date.timestamp(),
                manifest=manifest
            )

    def _claim_generator_id(self) -> int:
        """
        Finds all the generator ids which have not been reserved in the past PROBE_MISSES_TO_RELEASE liveliness
        checks, and then claims the first such generator id as reserved.
        """
        current_timestamp_ms = get_current_timestamp_ms()
        ms_since_last_committed_update = current_timestamp_ms - self._manifest
        released_ids = np.nonzero(ms_since_last_committed_update > self._ms_to_release_generator_id)[0]

        if len(released_ids) > 0:
            generator_id = released_ids[0]
            self._set_liveliness(
                current_timestamp_ms=current_timestamp_ms,
                generator_id=generator_id
            )
        else:
            raise OverflowError("All available generator ids are in use.")

        return generator_id

    def _set_liveliness(
            self,
            current_timestamp_ms: int,
            generator_id: int
    ) -> None:
        """
        Writes the latest timestamp at which the Snowfall instance is alive to the manifest.
        """
        self._manifest[generator_id] = current_timestamp_ms
        self._last_alive_ms = current_timestamp_ms
