# Snowfall
Snowfall is a lightweight 64-bit integer based GUID generator inspired by the Twitter-Snowflake algorithm. Compared to traditional 128-bit UUIDs, Snowfall generates IDs which:
1. Are k-sortable by creation time.
2. Have superior indexing characteristics on most DBMSes.
3. Take up half the space.

## GUID Specification
A Snowfall GUID consists of:
```
1  bit reserved
40 bits for the ms since a custom epoch time
12 bits for a looping counter
11 bits for a generator id
```

As such, Snowfall returns unique GUIDs for as long as:
1. The generator id is within `[0-2048)`.
2. No more than `4096` GUIDs are generated within one ms.
3. The lifetime of the system is no more than `2^41ms` (~70 years) from the epoch time set.

## Developer Guide
### Quickstart
To start generating IDs, simply create a `Snowfall` instance with a `generator_id`.
```
from snowfall import Snowfall

id_generator = Snowfall(
    generator_id=0
)
```
Successively calling `get_id()` will return valid GUIDs. Snowfall throttles the issuing speed to ensure that no more than 4096 GUIDs are generated per ms. 
```
id_generator.get_id()
>>> 4611686027683621110
id_generator.get_id()
>>> 6385725700183638596
```

### Enforcing unique `generator_ids`
The global uniqueness of Snowfall's IDs only hold if each Snowfall instance has a unique `generator_id`. Ideally, we want to throw an exception when an instance is initialized with a `generator_id` that is already in use. The `id_assigners` module contains classes that enforce this constraint by automating the assignment of `generator_ids` to Snowfall instances, using a shared manifest of available and reserved `generator_ids`. If all available `generator_ids` are reserved by active Snowfall instances, further attempts at instantiation would result in an `OverflowError`.

#### For single-process projects
For single-process projects, we provide a `SimpleIDAssigner` that records the manifest as a Python data structure. All Snowfall instances need to share the same SimpleAssigner instance.
```
from datetime import datetime
from snowfall import Snowfall
from snowfall.id_assigners import SimpleAssigner

id_assigner = SimpleAssigner(
    liveliness_probe_ms=5000
    epoch_start=datetime(2020, 1, 1)
)

id_generator = Snowfall(=
    id_assigner=id_assigner
)
```

#### For multi-process or distributed projects
For multi-process, multi-container projects, we need to persist the `generator_id` assignment and liveliness information to a database shared by all containers writing to the same schema. For this, we provide a `DatabaseAssigner` that supports any SQLAlchemy-compatible database.

> :warning: **Instantiating multiple assigners**: All database assigners wih the same `engine_url` need to share the same `epoch_start`.

> :warning: **Permissions required**: The `DatabaseAssigner` creates new tables `snowfall_properties` and `snowfall_manifest`, and performs CRUD operations on them.

```
from datetime import datetime
from snowfall import Snowfall
from snowfall.id_assigners import DatabaseAssigner

id_assigner = DatabaseAssigner(
    engine_url="postgresql://user:pass@host:port/db"
    liveliness_probe_ms=5000,
    epoch_start=datetime(2020, 1, 1)
)

id_generator = Snowfall(=
    id_assigner=id_assigner
)
```

#### Technical notes
A `generator_id` is reserved for as long as the Snowfall instance is capable of transmitting liveliness information to the generator manifest, and released when the last liveliness update was more than a set amount of time ago. This time is set with `liveliness_probe_ms`.

When a `generator_id` is released, it is not struck from the manifest. Instead, new Snowfall instances are able to reserve it. This is to eliminate the need for a separate client to run regular cleanup jobs on the manifest, and keeps Snowfall as lightweight as possible.

## Contributions
We are looking to add support for generators that implement the Snowfall GUID spec in other languages. Please contact [@lowjiajin](https://github.com/lowjiajin) for more details.
