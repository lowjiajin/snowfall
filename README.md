# Snowfall
Snowfall is a lightweight 64-bit integer based GUID generator inspired by the Twitter-Snowflake algorithm. Compared to traditional 128-bit UUIDs, Snowfall generates IDs which:
1. Are k-sortable by creation time.
2. Have superior indexing characteristics on most DBMSes.
3. Take up half the space.

## GUID Specification
A Snowfall GUID consists of:
```
41 bits for the ms since a custom epoch time
11 bits for a looping counter
12 bits for a generator id
```

As such, Snowfall returns unique GUIDs for as long as:
1. The generator id is within `[0, 4096)`.
2. No more than `2048` GUIDs are generated within one ms per generator id.
3. The lifetime of the system is no more than `2^41ms` (~70 years) from the epoch time set.

## User Guide
### Terminology
- *Snowfall instance:* The GUID generator, reserves a unique `generator_id`.
- *Syncer instance:* Associated with one generator. Ensures that no other generator in the schema group is using its `generator_id`.
- *Schema group:* A grouping of generators that always produce globally unique IDs.

### Installation
A minimal installation of Snowfall. This supports both the `SimpleSyncer`, and the `DatabaseSyncer` when used with SQLite.
```
pip install snowfall
```

#### DBMS-specific dependencies
However, because the `DatabaseSyncer` uses SQLAlchemy to connect to the database, there are optional dependencies depending on the DBMS used. For instance, MySQL requires the `MySQL-python` package, while PostgreSQL requires `psycopg2`. More information can be found in the [SQLAlchemy docs](https://docs.sqlalchemy.org/en/latest/core/engines.html).

For convenience, we have included the following pip extras:
```
pip install snowfall[postgres]
pip install snowfall[mysql]
pip install snowfall[oracle]
```

### Quickstart
To start generating IDs, simply create a schema group and start a `Snowfall`. 
```
from snowfall import Snowfall
from snowfall.generator_syncers import SimpleSyncer

SimpleSyncer.create_schema_group()
id_generator = Snowfall()
```
Successively calling `get_guid()` will return valid GUIDs. 

> :warning: **Possible throttling**: Snowfall throttles the issuing speed to ensure that no more than 2048 GUIDs are generated per ms.

```
id_generator.get_guid()
>>> 133494887688437760
id_generator.get_guid()
>>> 133494896085434368
```

### Enforcing unique `generator_ids`
The global uniqueness of Snowfall's GUIDs only hold if each Snowfall instance reserves a unique [`generator_id`](#guid-specification). Ideally, we want to automate the reservation of `generator_ids` by Snowfall instances, and their release when not in use.

The `generator_syncers` module contains classes that enforce this constraint, by updating a shared manifest. If all available `generator_ids` are reserved by active Snowfall instances, further attempts at instantiation would result in an `OverflowError`.

#### For single-process projects
While most usages of `Snowfall` apply to setups where GUIDs are produced concurrently by multiple machines and/or processes, we nevertheless support a non-networked solution for single-process use cases. E.g. test environments, local prototyping, etc.

The `SimpleSyncer` records the manifest in-memory, persistence to disk is not required for uniqueness. To set it up, create a new global schema group, and then bind the Snowfall instance to it.
```
from snowfall import Snowfall
from snowfall.generator_syncers import SimpleSyncer

SimpleSyncer.create_schema_group(
    schema_group_name="example_schema_group"
)

id_generator = Snowfall(
    generator_syncer_type=SimpleSyncer,
    schema_group_name="example_schema_group"
)
```

You can also customize the liveliness probe frequency and the epoch start as follows:

```
SimpleSyncer.create_schema_group(
    schema_group_name="example_schema_group"
    liveliness_probe_s=10
    epoch_start_date=datetime(2020, 1, 1)
)
```

#### For multi-process or distributed projects
When we have multiple `Snowfall` instances generating concurrently across multiple processes or machines, we need to persist the `generator_id` assignment and liveliness information to a database shared by all containers writing to the same schema. For this, we provide a `DatabaseSyncer` that supports any SQLAlchemy-compatible database.

> :warning: **Permissions required**: The `DatabaseSyncer` creates new tables `snowfall_{schema_group_name}_properties` and `snowfall_{schema_group_name}_manifest`, and performs CRUD operations on them.

First, create the schema group. Because this operation creates the relevant tables in the database of your choice, it should only be done once. You can also access this function via the terminal as `create_db_schema_group`.
```
from snowfall.generator_syncers import DatabaseSyncer

DatabaseSyncer.create_schema_group(
    schema_group_name="example_schema_group",
    engine_url="dbms://user:pass@host:port/db"
)
```

Next, just start a `Snowfall` anywhere you want, and point it to the schema group you created.
```
from snowfall import Snowfall

id_generator = Snowfall(=
    generator_syncer_type=DatabaseSyncer,
    schema_group_name="example_schema_group",
    engine_url="dbms://user:pass@host:port/db"
)
```

The `create_schema_group` method also supports other keyword arguments. Shown here are the defaults:
```
DatabaseSyncer.create_schema_group(
    liveliness_probe_s = 5,
    epoch_start_date = datetime(2020, 1, 1),
    max_claim_retries = 3,
    min_ms_between_claim_retries = 100,
    max_ms_between_claim_retries = 500,
    engine_url = "sqlite:////tmp/test.db"
)
```

Note that the default behaviour for the `engine_url` is to create a sqlite database in a temporary directory. We recommend switching this out for a client-server DBMS of your choice.

#### Technical notes
A `generator_id` is reserved for as long as the Snowfall instance is capable of transmitting liveliness information to the generator manifest, and released when the last liveliness update was more than a set amount of time ago. This time is set with `liveliness_probe_ms`.

When a `generator_id` is released, it is not struck from the manifest. Instead, new Snowfall instances are able to reserve it. This is to eliminate the need for a separate client to run regular cleanup jobs on the manifest, and keeps Snowfall as lightweight as possible.

## Contributions
We are looking to:
1) Add support for generators that implement the Snowfall GUID spec in other languages.
2) Improve the speed of Snowfall by converting the codebase to Cython.
3) Declare extras for the `pip install` process, to reduce unnecessary dependencies.

Please contact [@lowjiajin](https://github.com/lowjiajin) for more details.
