/*  _______ _     _         _____
 * |__   __(_)   | |       / ____|
 *    | |   _  __| | ___  | |  __  __ _ _   _  __ _  ___
 *    | |  | |/ _` |/ _ \ | | |_ |/ _` | | | |/ _` |/ _ \
 *    | |  | | (_| |  __/ | |__| | (_| | |_| | (_| |  __/
 *    |_|  |_|\__,_|\___|  \_____|\__,_|\__,_|\__, |\___|
 *                                             __/ |
 *                                            |___/
 * Author: Bryce Kellogg (bryce@kellogg.org)
 * Copyright: 2021 Bryce Kellogg
 * License: GPLv3
 */
#include <queue>
#include "Adafruit_LC709203F.h"

#define DEVICE_NAME  "tide-guage-1"

// The pin used to enable a sensor reading. To
// trigger a reading, hold low for at least 20 uS
#define SENSOR_ENABLE_PIN   D11  // Yellow wire
#define SEMSOR_GND_PIN      D13  // Black wire
#define SENSOR_VCC_PIN      D12  // Red wire
                                 // Brown wire -> UART RX

//
//
#define BATTERY_MONITOR_GND_PIN   D2
#define BATTERY_MONITOR_VCC_PIN   D3

// Because the queue used to pass sensor records
// allocates new records on the heap as they are
// passed in, we set a limit on the number of
// records the queue can hold. It will never get
// above this size. If the queue is full, new
// sensor records will be dropped.
#define MAX_RECORDS 100


// The maximum size of one of our sensor records as a JSON object.
// The size is determined by the JSON format, the object keys, and
// the maximum length of the values. For time value, we currently
// only support 32-bit unsigned ints, giving a maximum of 10 digits.
// For sensor values, the data is in mm and we will not get values
// from the sensor above 10 m (9999 mm), giving a max of 4 digits.
#define MAX_BYTES_PER_RECORD sizeof(R"([4294967295,{"distance":9999,"queue-size":999,"battery-percent":100.0}],)") + sizeof("]}")


// The maximum size of data that we can publish is
// set by the Particle Device OS spec to be 622 bytes.
//
// https://docs.particle.io/reference/device-os/firmware/boron/#particle-publish-
#define MAX_PUBLISH_SIZE 622


// The Particle cloud has a limit of 1 publish per second. In
// order to not get throttled by publishing too fast, we set
// a limit on the timer period for cloud update timers. Any calls
// to the config function with a cloud update timer period smaller
// than this value (in milliseconds) will be replaced by this value.
#define MIN_UPDATE_PERIOD 2000


// The time interval to use when syncing the
// onboard clock with the network time (in ms)
// We don't need to do it very often.
#define TIME_SYNC_TIMER_PERIOD 23*60*60*1000


/**
 * State of the state machine
 *
 */
// enum {
//     UNINITIALIZED,
// } state = UNINITIALIZED;



// A structure for saving sensor records. This
// is used to pass data into and out of the queue,
// and therefore between the sensing function and
// the cloud update function.
struct DataRecord {
    uint32_t timestamp;
    uint16_t distance;  // TODO: make a list of samples
    uint8_t  queuesize;
    float    batterypercent;
};


// Config params
// Periods are in milliseconds
int sensorPollingPeriod = 30*1000; // 30 seconds
int cloudUpdatePeriod = 5*60*1000; // 5 min
unsigned int numSamplesPerPoll = 1;


// Flags
bool doTimeSync = false;
bool doSensorPoll = false;
bool doCloudUpdate = false;
bool doDeviceInfoUpdate = false;


// Timer callbacks
void onTimeSyncTimer() { doTimeSync = true; }
void onSensorPollingTimer() { doSensorPoll = true; }
void onCloudUpdateTimer() { doCloudUpdate = true; }


// Software timers
Timer timeSyncTimer(TIME_SYNC_TIMER_PERIOD, onTimeSyncTimer);
Timer sensorPollingTimer(sensorPollingPeriod, onSensorPollingTimer);
Timer cloudUpdateTimer(cloudUpdatePeriod, onCloudUpdateTimer);


SerialLogHandler logHandler;

Adafruit_LC709203F batteryMonitor;


/**
 * Get a distance reading from the sensor.
 *
 * This function triggers a sonar sensor reading,
 * reads the resulting data over UART, parses the
 * UART result into an integer (in mm) and pushes
 * the data onto the back of the queue (if room).
 **/
bool sensorPolling(std::queue<DataRecord>& recordQueue) {

    // We can't collect a sample if the queue is full
    if (recordQueue.size() >= MAX_RECORDS) {
        Log.warn("Record queue full. Max size = %d", MAX_RECORDS);
        return false;
    }

    // The new record to store
    // data in before pushing
    // to the record queue.
    DataRecord record;

    // Pre-fill with non-sensor data
    record.timestamp = Time.now();
    record.batterypercent = batteryMonitor.cellPercent();
    record.queuesize = recordQueue.size();
    record.distance = 666;

    // Collect samples
    // for (unsigned int i = 0; i < numSamplesPerPoll; i++) {
    delay(500);

    // Trigger a read
    digitalWrite(SENSOR_ENABLE_PIN, HIGH);
    delay(1);
    digitalWrite(SENSOR_ENABLE_PIN, LOW);

    // Get reading from UART
    // char buffer[5] = "R012";  // Fake Data
    char buffer[5] = {0};
    int j = 0;
    char c = '\0';
    while ((c = Serial1.read()) != '\r' && j < sizeof(buffer)) {
        if (c != 0xFF) {
            buffer[j++] = c;
        }
    }
    //
    //     Log.info("Buffer Contents: %.5s", buffer);
    //
    // Parse UART and save to record
    sscanf(buffer, "R%d", &record.distance);

    // }


    // Save to queue
    recordQueue.push(record);

    return false;
}


/**
 * Publish sensor data to the cloud.
 *
 * This function pops sensor records off the queue,
 * compiles them into a JSON string, and publishes
 * them to the cloud. If the maximum size of data
 * that can be published is not large enough to empty
 * the queue, the function will schedule another run
 * via the `doCloudUpdate` flag. Will only publish at
 * a max rate defined by `MIN_UPDATE_PERIOD`.
 * Returns a boolean indicating if another update is needed.

 {
    "name": "tide-guage-1",
    "data": [
        [
            1689981501,
            {
                "distance": 100,
                "queue-size": 9,
                "battery-percent": 83.7
            }
        ]
    ]
 }








 **/
bool cloudUpdate(std::queue<DataRecord>& recordQueue) {

    static time_t lastPublish = 0;
    static char buff[MAX_PUBLISH_SIZE];


    // Nothing to do if the queue is empty
    if (recordQueue.empty()) {
        return false;
    }

    // Too soon since last publish
    if (Time.now() <= lastPublish+(MIN_UPDATE_PERIOD/1000)) {
        return true; // retry
    }




    int numRecords = 0;
    int numBytes = 0;

    // Begin saving as JSON array of JSON objects
    JSONBufferWriter json(buff, sizeof(buff)-1);
    json.beginObject();
    json.name("name").value(DEVICE_NAME);
    json.name("data");
    json.beginArray();

    // Save all the data in the queue unless
    // we run out of space in the buffer
    while (!recordQueue.empty() && json.bufferSize() > (json.dataSize() + MAX_BYTES_PER_RECORD)) {

        // Get data record from queue
        DataRecord record = recordQueue.front();
        recordQueue.pop();

        json.beginArray();
        json.value(String(record.timestamp));

        // Convert data record to JSON
        // We convert time to a String first
        // to get around type size limitations
        // of the JSON writer library.
        json.beginObject();
        json.name("distance").value(record.distance);
        json.name("queue-size").value(record.queuesize);
        json.name("battery-percent").value(record.batterypercent, 1);
        json.endObject();

        json.endArray();
    }

    json.endArray();
    json.endObject();

    // Null terminate the JSON string
    json.buffer()[std::min(json.bufferSize(), json.dataSize())] = '\0';

    // Publish data to cloud
    Particle.publish("data", buff);
    lastPublish = Time.now();

    // Try again if records still waiting
    return !recordQueue.empty();
}


/**
 * Sync device time with the cloud.
 *
 * Over time the on board clock can get out
 * of sync, so we ping the cloud every once
 * in a while to resync with network time.
 **/
bool timeSync() {
    Particle.syncTime();
    return false;
}


/**
 * A setup function that runs early. This allows
 * us to set the sensor control pin low early to
 * avoid unneeded sensor reads.
**/
void setPins() {
    pinMode(SENSOR_ENABLE_PIN, OUTPUT);
    pinMode(BATTERY_MONITOR_GND_PIN, OUTPUT);
    pinMode(BATTERY_MONITOR_VCC_PIN, OUTPUT);
    pinMode(SEMSOR_GND_PIN, OUTPUT);
    pinMode(SENSOR_VCC_PIN, OUTPUT);
    digitalWrite(SENSOR_ENABLE_PIN, LOW);
    digitalWrite(BATTERY_MONITOR_GND_PIN, LOW);
    digitalWrite(BATTERY_MONITOR_VCC_PIN, HIGH);
    digitalWrite(SEMSOR_GND_PIN, LOW);
    digitalWrite(SENSOR_VCC_PIN, HIGH);
}
STARTUP(setPins());


/**
 * Setup function that gets called once at start up. We
 * are guaranteed to have cloud connectivity when this
 * function is run. Registers config function and starts
 * all the timers with default timeout values.
 **/
void setup() {

    // TODO: read in config values (and subscribe to further reads)

    // Initialize serial library
    Serial1.begin(9600);

    // Initialize battery monitor
    batteryMonitor.begin();
    batteryMonitor.setPackSize(LC709203F_APA_1000MAH);

    // Start timers
    Log.info("Starting Timers");
    timeSyncTimer.start();
    sensorPollingTimer.start();
    cloudUpdateTimer.start();
}


/**
 * Simple main loop that repeated executes to run our
 * application code. All it does is check global flags
 * (set by timers) and call the corresponding functions.
 **/
void loop() {
    static std::queue<DataRecord> recordQueue;
    if (doTimeSync) doTimeSync = timeSync();
    if (doSensorPoll) doSensorPoll = sensorPolling(recordQueue);
    if (doCloudUpdate) doCloudUpdate = cloudUpdate(recordQueue);
}
