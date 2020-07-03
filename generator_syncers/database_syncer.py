from datetime import datetime
from sqlalchemy import create_engine

from generator_syncers.abstracts import BaseSyncer
from utils import get_current_timestamp_ms


class DatabaseSyncer(BaseSyncer):
    pass
