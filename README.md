# Tide Gauge
The unique characteristics of **The Mudflats** make tide predictions based on local
NOAA tidal stations not very reflective of the true water levels. It has long
seemed that both the timing and magnitude of high/low tides differ from the
predicted values.

This project implements a tide gauge monitoring system that measures water levels,
transmits the data to the cloud via LTE, and enables monitoring via an Android app.

## Cloud

### Database
All persistent data storage for the Tide Guage cloud infrastructure is
stored in [AWS DynamoDB](https://aws.amazon.com/dynamodb/) tables. DynamoDB is
a fully managed NoSQL Key-Value database.

> **Attributes:** each "item" (or row) in the database is a collection of
>  "attributes", where each attribute consists of a key-value pair. In this way,
>  every database item acts as a normal associative array, allowing access to
>  data values by the associated key. Note that each item can have whatever
>  attributes it wants, and (other than Primary Keys), does not need to have
>  the same attribute keys as other items.

> **Primary Keys:** these are special attributes that allow the database to
>  retrieve items based on the values of the primary keys and a query; generally,
>  queries only operate on the primary keys. A "partition key" is a unique
>  primary key that allows querying for an exact item (if used as the only
>  primary key) or a collection of items (if used as a composite primary key).
>  A "sort key" can be used with a partition key as a part of a composite
>  primary key. When using a composite primary key, the sort key determines the
>  sort order of items that share a partition key. The combination of partition
>  & sort keys must be unique.


#### Config Table

| devicename   | key1 | key2 | ... |
| ------------ | ---- | ---- | --- |
| tide-guage-1 |      |      |     | 
| tide-guage-2 |      |      |     |

The "Config Table" is used to represent the current state of various config
options. Each record/row is identified by a primary partition key devicename
that corresponds to a single device. The other attributes describe the current
state of that device.


#### Data Table
The database uses the schema descibed below:

| devicename   | timestamp  | key1 | key2 | ... |
| ------------ | -----------| ---- | ---- | --- |
| tide-guage-1 | 1689817855 |      |      |     | 
| tide-guage-1 | 1689817871 |      |      |     |


The "Data Table" is used to store all time series data in the system. Each
record/row is identified by the composite primary key (devicename, timestamp),
where devicename is the partition key & timestamp is the sort key. The other
attributes in a given record correspond to the data for that timestamp
for that specific device.


### REST API



POST /data
GET  /data?param=value
POST /config
GET  /config
```json
     {
         "id": "<str>",
         "data": {
             "<metric>": [
                 {"timestamp": <int>, "value": <number>},
                 {"timestamp": <int>, "value": <number>},
                 ...
             ],
             "<metric>": [
                 {"timestamp": <int>, "value": <number>},
                 {"timestamp": <int>, "value": <number>},
                 ...
             ],
             ...
         }
     }
```
## Android App

Device
------
- https://docs.particle.io/datasheets/boron/boron-datasheet/
- https://www.maxbotix.com/ultrasonic_sensors/mb7388.htm (with shielded cable)
- Molex Microfit 4x2
- https://voltaicsystems.com/2-watt-panel/
- https://voltaicsystems.com/f3511-microusb/

## Notes
```
>>> particle function call tide-gauge-1 config '{"sensorPollingPeriod": 1, "cloudUpdatePeriod": 2, "numSamplesPerPoll": 3, "deviceInfoUpdatePeriod": 4}'
>>> particle token create --never-expires
```

