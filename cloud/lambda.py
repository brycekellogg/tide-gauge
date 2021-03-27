import boto3
import json
from schema import *

from pprint import pprint

def process(event, context):
    print(event)
    return {
        'statusCode': 200,
        'body': 'OK'
    }



def saveSensorData(data, databaseName='MudFlatsTideData', tableName='SensorData'):
    """
    A helper function that saves sensor data to the AWS Timestream database.
    The incoming data is expected to be a string of JSON in the format:
         [
             {"id": <str>, "time": <int>, "data": <int>},
             {"id": <str>, "time": <int>, "data": <int>},
             ...
          ]
    This string is converted to JSON and validated to make sure it conforms
    to the data format schema. It is then written to the AWS Timestream
    database such that each element of the our array becomes a single database
    record with `data` being the MeasureValue, `time` providing the Time stamp
    in seconds (unix time), and `id` being a dimension of the record.
    """

    # Validate incoming data
    schema = Schema(And(Use(json.loads), [{'id': str, 'time': int, 'data': int}]))
    try: validated = schema.validate(data)
    except SchemaError as e: return {'statusCode': 400, 'body': 'invalid data'}

    # Convert into a format for Timestream Records
    records = [{}]*len(validated)
    for i,r in enumerate(validated):
        deviceID = r['id']
        data = r['data']
        time = r['time']
        record = {'Dimensions': [{'Name': 'id', 'Value': str(deviceID)}],
                  'MeasureName': 'dist',
                  'MeasureValue': str(data),
                  'MeasureValueType': 'DOUBLE',
                  'Time': str(time),
                  'TimeUnit': 'SECONDS'}
        records[i] = record

    # # Write data to Timestream
    client = boto3.client('timestream-write')
    response = client.write_records(DatabaseName=databaseName,
                                    TableName=tableName,
                                    Records=records)

    # Query was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def saveDeviceData(data, databaseName='MudFlatsTideData', tableName='DeviceData'):
    """
    A helper function that saves device data to the AWS Timestream database.
    The incoming data is expected to be string represenation of a JSON object
    of the following form:
             {
               "id": <str>,
               "time": <int>,
               "sensorPollingPeriod": <int>,
               "cloudUpdatePeriod": <int>,
               "numSamplesPerPoll": <int>,
               "deviceInfoUpdatePeriod": <int>,
               "batteryPercent": <float>,
               "queueSize": <int>
             }
    This string is converted to JSON and validated to make sure it conforms
    to the data format schema. It is then written to the AWS Timestream
    database as a series of records (one for each parameter, excluding id/time).
    The `id` entry is used as a dimension for each record, and the `time` entry
    as the Time stamp. All other entries are converted to their own record
    where they are saved as the main Measure.
    """

    # Validate incoming data
    schema = Schema(And(Use(json.loads), {"id": str,
                                          "time": int,
                                          "sensorPollingPeriod": int,
                                          "cloudUpdatePeriod": int,
                                          "numSamplesPerPoll": int,
                                          "deviceInfoUpdatePeriod": int,
                                          "batteryPercent": float,
                                          "queueSize": int}))
    try: validated = schema.validate(data)
    except SchemaError as e: return {'statusCode': 400, 'body': 'invalid data'}

    # Convert records into a format for Timestream Records
    records = []
    for key,value in validated.items():
        if key in ('id', 'time'): continue  # skip these, not data
        record = {'MeasureName': key, 'MeasureValue': str(value)}
        records.append(record)

    # Gather common attributes
    deviceID = validated['id']
    time = validated['time']
    attributes = {'Dimensions': [{'Name': 'id', 'Value': str(deviceID)}],
                  'Time': str(time),
                  'TimeUnit': 'SECONDS',
                  'MeasureValueType': 'DOUBLE'}

    # Write data to Timestream
    client = boto3.client('timestream-write')
    response = client.write_records(DatabaseName=databaseName,
                                    TableName=tableName,
                                    CommonAttributes=attributes,
                                    Records=records)

    # Query was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def readSensorData():
    pass


def readDeviceData():
    pass


def test():
    sampleSensorData = """
       [
         {"id": "e00fce683a5c196e475722dd", "time":1616790214, "data": 800},
         {"id": "e00fce683a5c196e475722dd", "time":1616790230, "data": 12}
       ]
       """

    sampleDeviceData = """
       {
         "id": "e00fce683a5c196e475722dd",
         "time": 1616790235,
         "sensorPollingPeriod": 2000,
         "cloudUpdatePeriod": 10000,
         "numSamplesPerPoll": 2,
         "deviceInfoUpdatePeriod": 30000,
         "batteryPercent": 1.2,
         "queueSize": 5
       }
       """

    # res = saveSensorData(sampleSensorData)
    # print(res)
    res = saveDeviceData(sampleDeviceData)
    print(res)


if __name__ == '__main__':
    test()
