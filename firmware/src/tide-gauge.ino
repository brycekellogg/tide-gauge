/*
 * Project tide-gauge
 * Description:
 * Author:
 * Date:
 */
#include <queue>

SerialLogHandler logHandler;


// Config params
// Periods are in milliseconds
unsigned int sensorPollingPeriod = 20000;
unsigned int cloudUpdatePeriod = 5000;
unsigned int numSamplesPerPoll = 20;
unsigned int deviceInfoUpdatePeriod = 60000;


// Software timers
Timer sensorPollingTimer(sensorPollingPeriod, onSensorPollingTimer);
Timer cloudUpdateTimer(cloudUpdatePeriod, onCloudUpdateTimer);
Timer deviceInfoUpdateTimer(deviceInfoUpdatePeriod, onDeviceInfoUpdateTimer);


// Flags
bool doSensorPoll = false;
bool doCloudUpdate = false;
bool doDeviceInfoUpdate = false;


// Timer callbacks
void onSensorPollingTimer() { doSensorPoll = true; }
void onCloudUpdateTimer() { doCloudUpdate = true; }
void onDeviceInfoUpdateTimer() { doDeviceInfoUpdate = true; }

struct SensorRecord {
    uint32_t time;
    uint16_t data;
};

#define MAX_RECORDS 100
std::queue<SensorRecord> globalRecordQueue;


//
//
#define MAX_BYTES_PER_RECORD sizeof(R"({"time": 4294967295, "data": 999},)")


// The maximum size of data that we can publish is
// set by the Particle Device OS spec to be 622 bytes.
//
// https://docs.particle.io/reference/device-os/firmware/boron/#particle-publish-
#define MAX_PUBLISH_SIZE 622


// TODO: can only do a publish per second max
#define MAX_PUBLISH_INTERVAL 2

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
    Log.info("Config function called");
    JSONObjectIterator iter(JSONValue::parseCopy(params));
    while(iter.next()) {
        JSONString paramName = iter.name();
        int paramValue = iter.value().toInt();

        Log.info("Config (%s, %d)", (const char*) paramName, paramValue);

        if (paramName == "sensorPollingPeriod") {
            // TODO: null handling
            sensorPollingPeriod = paramValue;
            sensorPollingTimer.changePeriod(sensorPollingPeriod);
        }

        if (paramName == "cloudUpdatePeriod") {
            // TODO: null handling
            cloudUpdatePeriod = paramValue;
            cloudUpdateTimer.changePeriod(cloudUpdatePeriod);
        }

        if (paramName == "numSamplesPerPoll") {
            numSamplesPerPoll = paramValue;
        }

        if (paramName == "deviceInfoUpdatePeriod") {
            // TODO: null handling
            deviceInfoUpdatePeriod = paramValue;
            deviceInfoUpdateTimer.changePeriod(deviceInfoUpdatePeriod);
        }
    }
    return 0;
}


void sensorPolling(std::queue<SensorRecord>& recordQueue) {
    for (unsigned int i = 0; i < numSamplesPerPoll; i++) {
        SensorRecord record;

        record.time = Time.now();
        record.data = random(20, 765);

        // Save to queue if we have room
        if (recordQueue.size() < MAX_RECORDS) {
            recordQueue.push(record);
        } else {
            Log.warn("Record queue full. Max size = %d", MAX_RECORDS);
        }
    }
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
 * a max rate defined by `MAX_PUBLISH_INTERVAL`.
 **/
void cloudUpdate(std::queue<SensorRecord>& recordQueue) {

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
           now > lastPublish+MAX_PUBLISH_INTERVAL) {

        // Get data record from queue
        auto record = recordQueue.front();
        recordQueue.pop();

        // Convert data record to JSON
        // We convert time to a String first
        // to get around type size limitations
        // of the JSON writer library.
        json.beginObject();
        json.name("time").value(String(record.time));
        json.name("data").value(record.data);
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
        Particle.publish("/tide-data/", buff);
        lastPublish = Time.now();
    }

    // Try again if records still waiting
    if (!recordQueue.empty()) {
        doCloudUpdate = true;
    }
}


void deviceInfoUpdate() {
    // Info to update:
    //    - battery percent
    //    - queue size
    //    - heap free
    //    - config params current values
    //    - USB voltage (via ADC) (can tell us about solar panel performance)

}


void setup() {
    // Register the config function
    Particle.function("config", functionConfig);

    // Start timers
    sensorPollingTimer.start();
    cloudUpdateTimer.start();
    /*deviceInfoUpdateTimer.start();*/

    Log.info("int -> %d", sizeof(int));
    Log.info("long -> %d", sizeof(long));
    Log.info("uint64_t -> %d", sizeof(uint64_t));
    Log.info("time -> %d", sizeof(time_t));
}


void loop() {
    /*Particle.publish("TestEvent", "{level: 9000}");*/

    if (doSensorPoll) {
        doSensorPoll = false;
        sensorPolling(globalRecordQueue);
    }

    if (doCloudUpdate) {
        doCloudUpdate = false;
        cloudUpdate(globalRecordQueue);
    }

    if (doDeviceInfoUpdate) {
        doDeviceInfoUpdate = false;
        Log.info("DEVICE INFO");
    }
}
