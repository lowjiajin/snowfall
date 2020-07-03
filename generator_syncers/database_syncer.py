from datetime import datetime
from sqlalchemy import create_engine

from generator_syncers.abstracts import BaseSyncer
from utils import get_current_timestamp_ms


class DatabaseSyncer(BaseSyncer):

    def __init__(
            self,
            schema_group_name: str = "default"
    ):
        """
        A DatabaseSyncer instance that reserves a generator_id for its associated Snowfall instance.
        :param schema_group_name: The schema group we want to associate this SimpleSyncer with.
        """
