from datetime import datetime
from time import sleep
from random import random
from typing import Tuple, Any
from sqlalchemy import create_engine, Column, String, SmallInteger, BigInteger, CheckConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.base import Engine

from snowfall.generator_syncers.abstracts import BaseSyncer
from snowfall.utils import get_current_timestamp_ms


class DatabaseSyncer(BaseSyncer):

    MAX_CLAIM_RETRIES = 3

    def __init__(
            self,
            engine_url: str = "sqlite:////tmp/test.db",
            schema_group_name: str = "default",
    ):
        """
        A DatabaseSyncer instance that reserves a generator_id for its associated Snowfall instance.
        :param engine_url: The URL to connect to the database: "dbms_type://user:pass@host:port/db"
        :param schema_group_name: The schema group we want to associate this SimpleSyncer with.
        """
        self.engine, self.session_factory, base = self._initialize_orm(engine_url)
        (
            self.manifest_table_name,
            self.properties_table_name,
            self.manifest_row_class,
            self.properties_class
        ) = self._generate_orm_classes(
            base=base,
            schema_group_name=schema_group_name
        )
        self._liveliness_probe_s, self._epoch_start_ms = self.get_properties()
        self._ms_to_release_generator_id = self._liveliness_probe_s * 1000 * self.PROBE_MISSES_TO_RELEASE
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
            epoch_start_date: datetime = datetime(2020, 1, 1),
            engine_url: str = "sqlite:////tmp/test.db"
    ) -> None:
        """
        Adds a schema group object to the class
        :param schema_group_name:  Unique name that identifies the schema group.
        :param liveliness_probe_s: Frequency with which the SimpleSyncer instances update their liveliness
                                    in the manifest.
        :param epoch_start_date:   GUIDs are unique for up to 2^41ms (~70 years) from the epoch start date.
        :param engine_url: The URL to connect to the database: "dbms_type://user:pass@host:port/db"
        """
        if epoch_start_date > datetime.utcnow():
            raise ValueError(f"epoch_start_date: {epoch_start_date} cannot be in the future of the current UTC time.")

        engine, session_factory, base = cls._initialize_orm(engine_url)
        manifest_table_name, properties_table_name, manifest_row_class, properties_class = cls._generate_orm_classes(
            base=base,
            schema_group_name=schema_group_name
        )
        cls._create_sql_tables(
            base=base,
            engine=engine,
            manifest_table_name=manifest_table_name,
            properties_table_name=properties_table_name
        )
        cls._insert_initial_rows(
            session_factory=session_factory,
            liveliness_probe_s=liveliness_probe_s,
            epoch_start_date=epoch_start_date,
            manifest_row_class=manifest_row_class,
            properties_class=properties_class
        )

    @staticmethod
    def _initialize_orm(
            engine_url: str
    ) -> Tuple[Engine, ScopedSession, Any]:
        """
        Instantiates the relevant engines, sessions, and base classes needed for the SQLAlchemy ORM to run.
        """
        engine = create_engine(engine_url)
        session_factory = scoped_session(sessionmaker(bind=engine))
        base = declarative_base()
        return engine, session_factory, base

    @staticmethod
    def _generate_orm_classes(
            base: Any,
            schema_group_name: str
    ) -> Tuple[str, str, Any, Any]:
        """
        Defines the base classes that map to tables in our DBMS, and their columns.
        """
        manifest_table_name = f"snowfall_{schema_group_name}_manifest"
        properties_table_name = f"snowfall_{schema_group_name}_properties"

        class ManifestRow(base):
            __tablename__ = manifest_table_name
            generator_id = Column(SmallInteger, primary_key=True)
            last_updated_ms = Column(BigInteger, nullable=False, default=0)
            race_condition_ticker = Column(SmallInteger, nullable=False, default=0)
            __table_args__ = (
                CheckConstraint("race_condition_ticker in (0, 1)"),
            )

        class Properties(base):
            __tablename__ = properties_table_name
            key = Column(String(16), primary_key=True)
            value = Column(BigInteger, nullable=False)

        return manifest_table_name, properties_table_name, ManifestRow, Properties

    @staticmethod
    def _create_sql_tables(
            base: Any,
            engine: Engine,
            manifest_table_name: str,
            properties_table_name: str
    ) -> None:
        """
        One-time operation to create the manifest and properties tables if they don't already exist.
        """
        if engine.dialect.has_table(engine, manifest_table_name):
            raise RuntimeError(f"Manifest for schema group: {manifest_table_name} already exists in database.")
        elif engine.dialect.has_table(engine, properties_table_name):
            raise RuntimeError(f"Properties for schema group: {properties_table_name} already exists in database.")
        else:
            base.metadata.create_all(engine)

    @classmethod
    def _insert_initial_rows(
            cls,
            session_factory: ScopedSession,
            liveliness_probe_s: int,
            epoch_start_date: datetime,
            manifest_row_class: Any,
            properties_class: Any
    ) -> None:
        """
        Populates the newly created manifest and properties tables with the correct data.
        """
        session = session_factory()
        manifest_rows = [
            manifest_row_class(generator_id=i) for i in range(cls.MAX_GENERATOR_ID)
        ]
        properties = [
            properties_class(key="liveliness_probe_s", value=liveliness_probe_s),
            properties_class(key="epoch_start_ms", value=epoch_start_date.timestamp())
        ]
        session.bulk_save_objects(manifest_rows)
        session.bulk_save_objects(properties)
        session.commit()
        session_factory.remove()

    def _claim_generator_id(self) -> int:
        """
        Finds all the generator ids which have not been reserved in the past PROBE_MISSES_TO_RELEASE liveliness
        checks, and then claims the first such generator id as reserved.
        """
        def try_to_claim():
            current_timestamp_ms = get_current_timestamp_ms()
            release_threshold_ms = current_timestamp_ms - self._ms_to_release_generator_id
            released = session.query(self.manifest_row_class) \
                .filter(self.manifest_row_class.last_updated_ms < release_threshold_ms) \
                .first()

            if released is not None:
                released_id = released.generator_id
                released.last_updated_ms = current_timestamp_ms
                if released.race_condition_ticker == 0:
                    released.race_condition_ticker += 1
                else:
                    released.race_condition_ticker -= 1
                session.commit()
                self._last_alive_ms = current_timestamp_ms
                return released_id
            else:
                raise OverflowError("All available generator ids are in use.")

        generator_id = None
        session = self.session_factory()
        tries = 0
        while generator_id is None and tries <= self.MAX_CLAIM_RETRIES:
            try:
                tries += 1
                generator_id = try_to_claim()
            except IntegrityError:
                sleep(random() / 5)
        self.session_factory.remove()

        if generator_id is not None:
            return generator_id
        else:
            raise RuntimeError("Cannot claim generator id due to persistent race conditions")

    def _set_liveliness(
            self,
            current_timestamp_ms: int,
            generator_id: int,
    ) -> None:
        """
        Writes the latest timestamp at which the Snowfall instance is alive to the manifest.
        """
        session = self.session_factory()
        session.query(self.manifest_row_class) \
            .filter_by(generator_id=generator_id) \
            .update({"last_updated_ms": current_timestamp_ms})
        session.commit()
        self.session_factory.remove()
        self._last_alive_ms = current_timestamp_ms

    def get_properties(self) -> Tuple[int, int]:
        session = self.session_factory()
        liveliness_probe_s = session.query(self.properties_class) \
            .filter_by(key="liveliness_probe_s") \
            .one().value
        epoch_start_ms = session.query(self.properties_class) \
            .filter_by(key="epoch_start_ms") \
            .one().value
        self.session_factory.remove()
        return liveliness_probe_s, epoch_start_ms