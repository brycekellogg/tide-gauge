#  _______ _     _         _____
# |__   __(_)   | |       / ____|
#    | |   _  __| | ___  | |  __  __ _ _   _  __ _  ___
#    | |  | |/ _` |/ _ \ | | |_ |/ _` | | | |/ _` |/ _ \
#    | |  | | (_| |  __/ | |__| | (_| | |_| | (_| |  __/
#    |_|  |_|\__,_|\___|  \_____|\__,_|\__,_|\__, |\___|
#                                             __/ |
#                                            |___/
# Author: Bryce Kellogg (bryce@kellogg.org)
# Copyright: 2021 Bryce Kellogg
# License: GPLv3
"""
Schema:



"""
import json
import os
from datetime import datetime
from pprint import pprint
import logging

logging.basicConfig(level=logging.DEBUG)

from schema import *
from sqlalchemy import *
from sqlalchemy.dialects import registry
registry.register("s3sqlite", "sqlalchemy-s3sqlite.dialect", "S3SQLiteDialect")


# Database info
meta = MetaData()

# +-----------+----------+
# | Field     | Type     |
# +-----------+----------+
# | id        | INT      |
# | deviceID  | VARCHAR  |
# | timestamp | DATETIME |
# | distance  | INT      |
# +---------+------------+
sensorData = Table('sensorData', meta,
                   Column('id', Integer, primary_key = True),
                   Column('deviceID', String(24)),
                   Column('timestamp', DateTime),
                   Column('distance', Integer))

# +------------------------+----------+
# | Field                  | Type     |
# +------------------------+----------+
# | id                     | INT      |
# | deviceID               | VARCHAR  |
# | timestamp              | DATETIME |
# | sensorPollingPeriod    | INT      |
# | cloudUpdatePeriod      | INT      |
# | numSamplesPerPoll      | INT      |
# | deviceInfoUpdatePeriod | INT      |
# | batteryPercent         | FLOAT    |
# | queueSize              | INT      |
# +------------------------+----------+
deviceData = Table('deviceData', meta,
                   Column('id', Integer, primary_key = True),
                   Column('deviceID', String(24)),
                   Column('timestamp', DateTime),
                   Column('sensorPollingPeriod', Integer),
                   Column('cloudUpdatePeriod', Integer),
                   Column('numSamplesPerPoll', Integer),
                   Column('deviceInfoUpdatePeriod', Integer),
                   Column('batteryPercent', Float),
                   Column('queueSize', Integer))

# # engine = create_engine('sqlite:///test.db')
# engine = create_engine('mysql+auroradataapi://:@/TideGaugeData', echo=True)
engine = create_engine('s3sqlite:///tide-data.sqlite', echo=True)
meta.create_all(engine)

def process(event, context):
    url = event['path']
    method = event['httpMethod']
    body = event['body']

    pprint(url)
    pprint(method)
    pprint(body)

    if url == '/sensor-data' and method == 'POST': return saveSensorData(body)
    if url == '/device-data' and method == 'POST': return print("saveDeviceData")
    if url == '/sensor-data' and method == 'GET':  return readSensorData()
    if url == '/device-data' and method == 'GET':  return print("readDeviceData")
    return {
        'statusCode': 400,
        'body': 'Bad Request'
    }



def saveSensorData(body):
    """
    A helper function that saves sensor data to the AWS database.
    The incoming data is expected to be a string of JSON in the format:
        {
            "id": <str>,
            "records": [
                {"time": <int>, "data": <int>},
                {"time": <int>, "data": <int>},
                ...
            ]
        }
    This string is converted to JSON and validated to make sure it conforms
    to the data format schema. It is then written to the AWS database such
    that each element of the our array becomes a single database record.
    """

    # Validate incoming data
    schema = Schema(And(Use(json.loads), {'id': str, 'records': [{'time': Use(int), 'data': int}]}))
    try: body = schema.validate(body)
    except SchemaError as e: return {'statusCode': 400, 'body': 'invalid data'}

    # Build list of records from input JSON
    records = []
    for r in body['records']:
        deviceID = body['id']
        distance = r['data']
        timestamp = datetime.utcfromtimestamp(r['time'])
        record = {'deviceID': deviceID,
                  'timestamp': timestamp,
                  'distance': distance}
        records.append(record)


    # Insert data into the `sensorData` table in databse
    result = engine.connect().execute(sensorData.insert(), records)

    # Query was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def saveDeviceData(body):
    """
    A helper function that saves device data to the AWS database.
    The incoming data is expected to be a string of JSON in the format:
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
    to the data format schema. It is then written to the AWS database as a
    single database record.
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
    try: body = schema.validate(data)
    except SchemaError as e: return {'statusCode': 400, 'body': 'invalid data'}

    # Build list of records from input JSON
    deviceID = body['id']
    timestamp = datetime.utcfromtimestamp(body['time'])
    sensorPollingPeriod = body['sensorPollingPeriod']
    cloudUpdatePeriod = body['cloudUpdatePeriod']
    numSamplesPerPoll = body['numSamplesPerPoll']
    deviceInfoUpdatePeriod = body['deviceInfoUpdatePeriod']
    batterPercent = body['batteryPercent']
    queueSize = body['queueSize']

    records = [{'deviceID': deviceID,
                'timestamp': timestamp,
                'sensorPollingPeriod': sensorPollingPeriod,
                'cloudUpdatePeriod': cloudUpdatePeriod,
                'numSamplesPerPoll': numSamplesPerPoll,
                'deviceInfoUpdatePeriod': deviceInfoUpdatePeriod,
                'batteryPercent': batteryPercent,
                'queueSize': queueSize}]

    # Insert data into the `deviceData` table in databse
    result = engine.connect().execute(deviceData.insert(), records)

    # Query was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def readSensorData():
    """

        [
            {"id", <int>, "deviceID", <str>, "timestamp": <str>, "distance": <int>},
            {"id", <int>, "deviceID", <str>, "timestamp": <str>, "distance": <int>},
            ...
        ]


    """

    # Perform query on `sensorData` table in database
    results = engine.connect().execute(sensorData.select())

    # Convert database result to JSON output format
    records = []
    for r in results:
        recordID = r[0]
        deviceID = r[1]
        timestamp = r[2].isoformat()
        distance = r[3]
        record = {'id': recordID,
                  'deviceID': deviceID,
                  'timestamp': timestamp,
                  'distance': distance}
        records.append(record)

    # Return data
    return {
        'statusCode': 200,
        'body': json.dumps(records)
    }


def readDeviceData(databaseName='MudFlatsTideData', tableName='DeviceData'):
    """
         [
             {
                "id": <int>,
                "deviceID": <str>,
                "timestamp": <str>,
                "sensorPollingPeriod": <int>,
                "cloudUpdatePeriod": <int>,
                "numSamplesPerPoll": <int>,
                "deviceInfoUpdatePeriod": <int>,
                "batteryPercent": <float>,
                "queueSize": <int>
            },
             ...
          ]
    """
    # Perform query on `deviceData` table in database
    results = engine.connect().execute(deviceData.select())

    # Convert database result to JSON output format
    records = []
    for r in results:
        recordID = r[0]
        deviceID = r[1]
        timestamp = r[2].isoformat()
        sensorPollingPeriod = r[3]
        cloudUpdatePeriod = r[4]
        numSamplesPerPoll = r[5]
        deviceInfoUpdatePeriod = r[6]
        batterPercent = r[7]
        queueSize = r[8]

        record = {'id': recordID,
                  'deviceID': deviceID,
                  'timestamp': timestamp,
                  'sensorPollingPeriod': sensorPollingPeriod,
                  'cloudUpdatePeriod': cloudUpdatePeriod,
                  'numSamplesPerPoll': numSamplesPerPoll,
                  'deviceInfoUpdatePeriod': deviceInfoUpdatePeriod,
                  'batteryPercent': batteryPercent,
                  'queueSize': queueSize}
        records.append(record)

    # Return data
    return {
        'statusCode': 200,
        'body': json.dumps(records)
    }

