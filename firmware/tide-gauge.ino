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

// The pin used to enable a sensor reading. To
// trigger a reading, hold low for at least 20 uS
#define SENSOR_ENABLE_PIN   D11
#define SEMSOR_GND_PIN      D13
#define SENSOR_VCC_PIN      D12

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
#define MAX_BYTES_PER_RECORD sizeof(R"({"time": 4294967295, "data": 9999},)")


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


// A structure for saving sensor records. This
// is used to pass data into and out of the queue,
// and therefore between the sensing function and
// the cloud update function.
struct SensorRecord {
    uint32_t time;
    uint16_t data;
};


// Config params
// Periods are in milliseconds
int sensorPollingPeriod = 5*1000; //20*20*1000;
int cloudUpdatePeriod = 30*1000; //20*30*1000;
int deviceInfoUpdatePeriod = 1*30*1000;
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
void onDeviceInfoUpdateTimer() { doDeviceInfoUpdate = true; }


// Software timers
Timer timeSyncTimer(TIME_SYNC_TIMER_PERIOD, onTimeSyncTimer);
Timer sensorPollingTimer(sensorPollingPeriod, onSensorPollingTimer);
Timer cloudUpdateTimer(cloudUpdatePeriod, onCloudUpdateTimer);
Timer deviceInfoUpdateTimer(deviceInfoUpdatePeriod, onDeviceInfoUpdateTimer);


SerialLogHandler logHandler;

Adafruit_LC709203F batteryMonitor;

/**
 * A Particle Function for setting device config parameters.
 *
 * This is how we configure the device and the various config
 * parameters for it defined above. The function takes a single
 * string representing a JSON object where each key is a congfig
 * variable name and the corresponding value is the desired int
 * value of the config parameter. Only the config params that
 * you want to update need to be specified in the JSON object.
 * To stop a certain timer, pass null as the config param value.
 *
 *      '{"sensorPollingPeriod": <int>,
 *        "cloudUpdatePeriod": <int>,
 *        "numSamplesPerPoll": <int>,
 *        "deviceInfoUpdatePeriod": <int>}'
 *
 * >>> particle function call tide-gauge-1 config <jsonData>
 **/
int functionConfig(String params) {
    JSONObjectIterator iter(JSONValue::parseCopy(params));
    while(iter.next()) {
        JSONString paramName = iter.name();
        JSONValue  paramValue = iter.value();

        Log.info("Config (%s, %s)", (const char*) paramName, (const char*) paramValue.toString());

        if (paramName == "sensorPollingPeriod") {
            if (paramValue.isNumber()) {
                sensorPollingPeriod = paramValue.toInt();
                sensorPollingTimer.changePeriod(sensorPollingPeriod);
            } else if (paramValue.isNull()) {
                sensorPollingPeriod = -1;
                sensorPollingTimer.stop();
            }
        }

        if (paramName == "cloudUpdatePeriod") {
            if (paramValue.isNumber()) {
                cloudUpdatePeriod = paramValue.toInt();

                // We don't want to update faster than a certain limit
                if (cloudUpdatePeriod < MIN_UPDATE_PERIOD) cloudUpdatePeriod = MIN_UPDATE_PERIOD;

                cloudUpdateTimer.changePeriod(cloudUpdatePeriod);
            } else if (paramValue.isNull()) {
                cloudUpdatePeriod = -1;
                cloudUpdateTimer.stop();
            }
        }

        if (paramName == "numSamplesPerPoll" && paramValue.isNumber()) {
            numSamplesPerPoll = paramValue.toInt();
        }

        if (paramName == "deviceInfoUpdatePeriod") {
            if (paramValue.isNumber()) {
                deviceInfoUpdatePeriod = paramValue.toInt();

                // We don't want to update faster than a certain limit
                if (deviceInfoUpdatePeriod < MIN_UPDATE_PERIOD) deviceInfoUpdatePeriod = MIN_UPDATE_PERIOD;

                deviceInfoUpdateTimer.changePeriod(deviceInfoUpdatePeriod);
            } else if (paramValue.isNull()) {
                deviceInfoUpdatePeriod = -1;
                deviceInfoUpdateTimer.stop();
            }
        }
    }
    return 0;
}


/**
 * Get a distance reading from the sensor.
 *
 * This function triggers a sonar sensor reading,
 * reads the resulting data over UART, parses the
 * UART result into an integer (in mm) and pushes
 * the data onto the back of the queue (if room).
 **/
bool sensorPolling(std::queue<SensorRecord>& recordQueue) {
    for (unsigned int i = 0; i < numSamplesPerPoll; i++) {
        delay(500);
        SensorRecord record;

        record.time = Time.now();

        // Trigger a read
        digitalWrite(SENSOR_ENABLE_PIN, HIGH);
        delay(1);
        digitalWrite(SENSOR_ENABLE_PIN, LOW);

        // Get reading from UART
        char buffer[5] = "R012";  // Fake Data
        /*char buffer[5] = {0};*/
        /*int j = 0;*/
        /*char c = '\0';*/
        /*while ((c = Serial1.read()) != '\r') {*/
        /*    if (c != 0xFF) {*/
        /*        buffer[j++] = c;*/
        /*    }*/
        /*}*/

        Log.info("Buffer Contents: %.5s", buffer);

        // Parse UART and save to record
        sscanf(buffer, "R%d", &record.data);

        // Save to queue if we have room
        if (recordQueue.size() < MAX_RECORDS) {
            recordQueue.push(record);
        } else {
            Log.warn("Record queue full. Max size = %d", MAX_RECORDS);
        }
    }
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
 **/
bool cloudUpdate(std::queue<SensorRecord>& recordQueue) {

    Log.info("Begin Cloud Update");
    static time_t lastPublish = 0;
    static char buff[MAX_PUBLISH_SIZE];

    int numRecords = 0;
    int numBytes = 0;
    time_t now = Time.now();

    // Begin saving as JSON array of JSON objects
    JSONBufferWriter json(buff, sizeof(buff)-1);
    json.beginArray();

    // Save all the data in the queue unless
    // we run out of space in the buffer,
    // or we are publishing too fast.
    while (!recordQueue.empty() &&
           json.bufferSize() > numBytes+MAX_BYTES_PER_RECORD+sizeof("]") &&
           now > lastPublish+(MIN_UPDATE_PERIOD/1000)) {

        // Get data record from queue
        auto record = recordQueue.front();
        recordQueue.pop();

        // Convert data record to JSON
        // We convert time to a String first
        // to get around type size limitations
        // of the JSON writer library.
        json.beginObject();
        json.name("time").value(String(record.time));
        json.name("dist").value(record.data);
        json.endObject();

        // Save info about JSON progress
        numBytes = json.dataSize();
        numRecords++;
    }

    // Terminate the JSON string
    json.endArray();
    numBytes = json.dataSize();
    json.buffer()[numBytes] = '\0';

    // Publish data (if any) to cloud
    if (numRecords > 0) {
        Log.info("Publishing: %d records for %d bytes", numRecords, numBytes);
        Particle.publish("sensor-data", buff);
        lastPublish = Time.now();
    }

    // Try again if records still waiting
    return !recordQueue.empty();
}


/**
 * Publish device info to the cloud.
 *
 * This function gathers various info about the
 * device and publishes it to the cloud as a JSON
 * object. Each key describes the device property
 * name with the value representing the property
 * value at the time this function is called.
 *
 *      '{"time": <int>,
 *        "sensorPollingPeriod": <int>,
 *        "cloudUpdatePeriod": <int>,
 *        "numSamplesPerPoll": <int>,
 *        "deviceInfoUpdatePeriod": <int>,
 *        "batteryPercent": <float>,
 *        "queueSize": <int>}'
 *
 * Returns a boolean indicating if another update
 * is needed. Currently never needed; always false.
 **/
bool deviceInfoUpdate(std::queue<SensorRecord>& recordQueue) {

    static char buff[MAX_PUBLISH_SIZE];

    // Get values that need measuring
    float batteryPercent = batteryMonitor.cellPercent();
    int queueSize = recordQueue.size();
    size_t timestamp = Time.now();
    String batteryStateStr;

    // Saving as JSON object
    JSONBufferWriter json(buff, sizeof(buff)-1);
    json.beginObject();
    json.name("time").value(String(timestamp));
    json.name("sensorPollingPeriod").value(sensorPollingPeriod);
    json.name("cloudUpdatePeriod").value(cloudUpdatePeriod);
    json.name("numSamplesPerPoll").value(numSamplesPerPoll);
    json.name("deviceInfoUpdatePeriod").value(deviceInfoUpdatePeriod);
    json.name("batteryPercent").value(batteryPercent);
    json.name("queueSize").value(queueSize);
    json.endObject();

    // Terminate the JSON string
    json.buffer()[json.dataSize()] = '\0';

    // Publish data to cloud & log
    Log.info("sensorPollingPeriod = %d", sensorPollingPeriod);
    Log.info("cloudUpdatePeriod = %d", cloudUpdatePeriod);
    Log.info("numSamplesPerPoll = %d", numSamplesPerPoll);
    Log.info("deviceInfoUpdatePeriod = %d", deviceInfoUpdatePeriod);
    Log.info("batteryPercent = %.2f", batteryPercent);
    Log.info("queueSize = %d", queueSize);
    Particle.publish("device-data", buff);

    return false;
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

    // Register the config function
    Particle.function("config", functionConfig);

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
    deviceInfoUpdateTimer.start();
}


/**
 * Simple main loop that repeated executes to run our
 * application code. All it does is check global flags
 * (set by timers) and call the corresponding functions.
 **/
void loop() {
    static std::queue<SensorRecord> recordQueue;
    if (doTimeSync) doTimeSync = timeSync();
    if (doSensorPoll) doSensorPoll = sensorPolling(recordQueue);
    if (doCloudUpdate) doCloudUpdate = cloudUpdate(recordQueue);
    if (doDeviceInfoUpdate) doDeviceInfoUpdate = deviceInfoUpdate(recordQueue);
}
