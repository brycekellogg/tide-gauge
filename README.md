Tide Gauge
==========
The unique characteristics of **The Mudflats** make tide predictions based on local
NOAA tidal stations not very reflective of the true water levels. It has long
seemed that both the timing and magnitude of high/low tides differ from the
predicted values.

This project implements a tide gauge monitoring system that measures water levels,
transmits the data to the cloud via LTE, and enables monitoring via an Android app.

Device
------
- https://docs.particle.io/datasheets/boron/boron-datasheet/
- https://www.maxbotix.com/ultrasonic_sensors/mb7388.htm (with shielded cable)
- Molex Microfit 4x2
- https://voltaicsystems.com/2-watt-panel/
- https://voltaicsystems.com/f3511-microusb/

## Cloud

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


## Notes
```
>>> particle function call tide-gauge-1 config '{"sensorPollingPeriod": 1, "cloudUpdatePeriod": 2, "numSamplesPerPoll": 3, "deviceInfoUpdatePeriod": 4}'
>>> particle token create --never-expires
```

