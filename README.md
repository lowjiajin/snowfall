# Snowfall
Snowfall is a lightweight 64-bit integer based GUID generator inspired by the Twitter-Snowflake algorithm. Compared to traditional 128-bit UUIDs, Snowfall generates IDs which:
1. Are k-sortable by creation time.
2. Have superior indexing characteristics on most DBMSes.
3. Take up half the space.

## Technicalities
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
#### Quickstart
To start generating IDs, simply create a `Snowfall` instance with a `generator_id`, and then call `get_id()`
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
