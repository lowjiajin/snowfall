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
2. No more than `2048` GUIDs are generated within one ms.
3. The lifetime of the system is no more than `2^41ms` (~70 years) from the epoch time set.

## Developer Guide
### Installation
A complete installation of Snowfall with all [`id_assigners`](#enforcing-unique-generator_ids) and their dependencies.
```
pip install snowfall
```

### Quickstart
To start generating IDs, simply create a `Snowfall`.
```
from snowfall import Snowfall

id_generator = Snowfall()
```
Successively calling `get_guid()` will return valid GUIDs. 

> :warning: **Possible throttling**: Snowfall throttles the issuing speed to ensure that no more than 2048 GUIDs are generated per ms.

```
id_generator.get_guid()
>>> 4611686027683621110
id_generator.get_guid()
>>> 6385725700183638596
```

### Enforcing unique `generator_ids`
The global uniqueness of Snowfall's IDs only hold if each Snowfall instance has a unique `generator_id`. Ideally, we want to throw an exception when an instance is initialized with a `generator_id` that is already in use. 

The `id_assigners` module contains classes that enforce this constraint by automating the assignment of `generator_ids` to Snowfall instances, using a shared manifest of available and reserved `generator_ids`. If all available `generator_ids` are reserved by active Snowfall instances, further attempts at instantiation would result in an `OverflowError`.

#### For single-process projects
For single-process projects, we provide a `SimpleIDAssigner` that records the _manifest as a Python data structure. First, create a new global schema group, and then bind the Snowfall instance to it.
```
from datetime import datetime
from snowfall import Snowfall
from snowfall.id_assigners.simple_assigner import SimpleAssigner

SimpleAssigner.create_schema_group(
    schema_group_name="example_schema_group"
)

id_generator = Snowfall(
    id_assigner_type=SimpleAssigner,
    schema_group_name="example_schema_group"
)
```

You can also customize the liveliness probe frequency and the epoch start as follows:

```
SimpleAssigner.create_schema_group(
    schema_group_name="example_schema_group"
    liveliness_probe_s=10
    epoch_start=datetime(2020, 1, 1)
)
```

#### For multi-process or distributed projects
For multi-process, multi-container projects, we need to persist the `generator_id` assignment and liveliness information to a database shared by all containers writing to the same schema. For this, we provide a `DatabaseAssigner` that supports any SQLAlchemy-compatible database.

> :warning: **Instantiating assigners**: All database assigners wih the same `engine_url` need to share the same `epoch_start` Otherwise, a ValueError is thrown.

> :warning: **Permissions required**: The `DatabaseAssigner` creates new tables `snowfall_properties` and `snowfall__manifest`, and performs CRUD operations on them.

```
from datetime import datetime
from snowfall import Snowfall
from snowfall.id_assigners.database_assigner import DatabaseAssigner

DatabaseAssigner.create_schema_group(
    schema_group_name="example_schema_group"
    liveliness_probe_s=10,
    epoch_start=datetime(2020, 1, 1)
)

id_generator = Snowfall(=
    id_assigner_type=DatabaseAssigner,
    engine_url="postgresql://user:pass@host:port/db"
)
```

#### Technical notes
A `generator_id` is reserved for as long as the Snowfall instance is capable of transmitting liveliness information to the generator manifest, and released when the last liveliness update was more than a set amount of time ago. This time is set with `liveliness_probe_ms`.

When a `generator_id` is released, it is not struck from the manifest. Instead, new Snowfall instances are able to reserve it. This is to eliminate the need for a separate client to run regular cleanup jobs on the manifest, and keeps Snowfall as lightweight as possible.

## Contributions
We are looking to:
1) Add support for generators that implement the Snowfall GUID spec in other languages.
2) Improve the speed of Snowfall by converting the codebase to Cython.
3) Declare extras for the `pip install` process, to reduce unnecessary dependencies.

Please contact [@lowjiajin](https://github.com/lowjiajin) for more details.
