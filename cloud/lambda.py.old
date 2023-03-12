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
import json
import os
from datetime import datetime
from pprint import pprint
import logging

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

engine = create_engine('s3sqlite:///tide-data.sqlite', echo=True)
# meta.create_all(engine)


def process(event, context):
    """
    The main handler for the lambda function. Extracts the needed data
    from the HTTP event and calls one of the helper functions based on
    the path and HTTP method. If there is no match, return an error.
    """
    url = event['path']
    method = event['httpMethod']
    body = event['body']
    queryStringParams = event['multiValueQueryStringParameters']

    print(queryStringParams)

    # Call correct helper function based on path & method
    if url == '/sensor-data' and method == 'POST': return saveSensorData(body)
    if url == '/device-data' and method == 'POST': return saveDeviceData(body)
    if url == '/sensor-data' and method == 'GET':  return readSensorData(queryStringParams)
    if url == '/device-data' and method == 'GET':  return readDeviceData(queryStringParams)
    if url == '/sensor-data' and method == 'DELETE': return deleteSensorData(queryStringParams)
    if url == '/device-data' and method == 'DELETE': return deleteDeviceData(queryStringParams)

    # If we make it here, something is wrong
    return {
        'statusCode': 400,
        'body': 'Bad Request'
    }


def filter(table, query, params, eqFields=[], cmpFields=[]):
    """
    A helper function that filters a sqlAlchemy select call
    based on HTTP querystring parameters. There are two types
    of fields we can filter on: eqFields only support equality
    testing, cmpFields support less than, greater then, etc.

    The format of the queryparams must be:
        {
            '<fieldName>': [<value>, <value>, ...],  # for eqFields
            '<fieldName_op>': [<value>],             # for cmpFields
            ...
        }
    A result will be included if it satisfies all conditions in the
    params dict. For eqParams, the field must equal any value supplied
    in the list. For cmpParams, the following operators are supported:
       - eq   the field must equal this value
       - lt   the field must be less than this value
       - gt   the field must be greater than this value
       - lte  the field must be less than or equal to this value
       - gte  the field must be greater than or equal to this value
    Multiple ops may be used for a single field (like for testing a range).
    """
    # Skip if there's no params
    if params == None: return query

    # Filter results with simple equality
    for field in eqFields:
        if field in params.keys():
            if field == 'limit':
                query = query.limit(int(params[field][0]))
            else:
                query = query.where(table.c[field].in_(params[field]))

    # Filter results with comparisons
    for field in cmpFields:
        for param in params.keys():
            if field in param:
                _, op = param.split('_')
                print(f"field={field}, op={op}, params={params[param]}")
                if field != 'timestamp':
                    if op == 'eq':  query = query.where(table.c[field].in_(params[param]))
                    if op == 'lt':  query = query.where(table.c[field] < params[param][0])
                    if op == 'gt':  query = query.where(table.c[field] > params[param][0])
                    if op == 'lte': query = query.where(table.c[field] <= params[param][0])
                    if op == 'gte': query = query.where(table.c[field] >= params[param][0])
                else:
                    if op == 'eq':  query = query.where(table.c[field].in_(func.datetime(params[param])))
                    if op == 'lt':  query = query.where(table.c[field] < func.datetime(params[param][0]))
                    if op == 'gt':  query = query.where(table.c[field] > func.datetime(params[param][0]))
                    if op == 'lte': query = query.where(table.c[field] <= func.datetime(params[param][0]))
                    if op == 'gte': query = query.where(table.c[field] >= func.datetime(params[param][0]))

    # Done filtering
    return query


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
    try: body = schema.validate(body)
    except SchemaError as e: return {'statusCode': 400, 'body': 'invalid data'}

    # Build list of records from input JSON
    deviceID = body['id']
    timestamp = datetime.utcfromtimestamp(body['time'])
    sensorPollingPeriod = body['sensorPollingPeriod']
    cloudUpdatePeriod = body['cloudUpdatePeriod']
    numSamplesPerPoll = body['numSamplesPerPoll']
    deviceInfoUpdatePeriod = body['deviceInfoUpdatePeriod']
    batteryPercent = body['batteryPercent']
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


def readSensorData(queryStringParams):
    """
    A function for handling reading sensor data from the database. The results
    are returned as a strong of JSON in the format:
        [
            {"id", <int>, "deviceID", <str>, "timestamp": <str>, "distance": <int>},
            {"id", <int>, "deviceID", <str>, "timestamp": <str>, "distance": <int>},
            ...
        ]
    The request can be limited using the HTTP query string. The following query
    params are supported:
      - id=<value>
      - deviceID=<value>
      - timestamp_eq=<value>
      - timestamp_lt=<value>
      - timestamp_gt=<value>
      - timestamp_lte=<value>
      - timestamp_gte=<value>
    The id and deviceID params can be supplied multiple times to select all
    rows that match any supplied param.
    """
    query = sensorData.select()

    # Select records based on filter
    query = filter(sensorData, query, queryStringParams,
                   eqFields=['id', 'deviceID', 'limit'],
                   cmpFields=['timestamp'])

    # Always order by timestamp, but to make limiting
    # work how we want, order opposite the way we want
    # to return results.
    query = query.order_by(sensorData.c.timestamp.desc())


    # Perform query on `sensorData` table in database
    results = engine.connect().execute(query)


    # Convert database result to JSON output format
    records = []
    for row in results:
        recordID = row._mapping['id']
        deviceID = row._mapping['deviceID']
        timestamp = row._mapping['timestamp'].isoformat()
        distance = row._mapping['distance']
        record = {'id': recordID,
                  'deviceID': deviceID,
                  'timestamp': timestamp,
                  'distance': distance}
        records.append(record)

    # We want to return results where the oldest
    # records are at the lowest indices.
    records.reverse()

    # Return data
    return {
        'statusCode': 200,
        'body': json.dumps(records)
    }


def readDeviceData(queryStringParams):
    """
    A function for handling reading sensor data from the database. The results
    are returned as a strong of JSON in the format:
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
    The request can be limited using the HTTP query string. The following query
    params are supported:
      - id=<value>
      - deviceID=<value>
      - timestamp_eq=<value>
      - timestamp_lt=<value>
      - timestamp_gt=<value>
      - timestamp_lte=<value>
      - timestamp_gte=<value>
    The id and deviceID params can be supplied multiple times to select all
    rows that match any supplied param.
    """
    query = deviceData.select()

    # Select records based on filter
    query = filter(deviceData, query, queryStringParams,
                   eqFields=['id', 'deviceID', 'limit'],
                   cmpFields=['timestamp'])

    # Always order by timestamp, but to make limiting
    # work how we want, order opposite the way we want
    # to return results.
    query = query.order_by(deviceData.c.timestamp.desc())


    # Perform query on `deviceData` table in database
    results = engine.connect().execute(query)

    # Convert database result to JSON output format
    records = []
    for row in results:
        recordID = row._mapping['id']
        deviceID = row._mapping['deviceID']
        timestamp = row._mapping['timestamp'].isoformat()
        sensorPollingPeriod = row._mapping['sensorPollingPeriod']
        cloudUpdatePeriod = row._mapping['cloudUpdatePeriod']
        numSamplesPerPoll = row._mapping['numSamplesPerPoll']
        deviceInfoUpdatePeriod = row._mapping['deviceInfoUpdatePeriod']
        batteryPercent = row._mapping['batteryPercent']
        queueSize = row._mapping['queueSize']

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

    # We want to return results where the oldest
    # records are at the lowest indices.
    records.reverse()

    # Return data
    return {
        'statusCode': 200,
        'body': json.dumps(records)
    }


def deleteSensorData(queryStringParams):
    """
    A function for handling deleting sensor data from the database.
    The request must be limited using the HTTP query string with the `id`
    parameter. The id params can be supplied multiple times to delete all
    rows that match any supplied id.
    """

    # Must supply id param
    if queryStringParams is None or 'id' not in queryStringParams.keys():
        return {
            'statusCode': 400,
            'body': 'Bad Request: missing id'
        }

    # Build query
    query = sensorData.delete()
    query = filter(sensorData, query, queryStringParams, eqFields=['id'])

    # Perform query on `sensorData` table in database
    results = engine.connect().execute(query)

    # Query was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def deleteDeviceData(queryStringParams):
    """
    A function for handling deleting device data from the database.
    The request must be limited using the HTTP query string with the `id`
    parameter. The id params can be supplied multiple times to delete all
    rows that match any supplied id.
    """
    # Must supply id param
    if queryStringParams is None or 'id' not in queryStringParams.keys():
        return {
            'statusCode': 400,
            'body': 'Bad Request: missing id'
        }

    # Build query
    query = deviceData.delete()
    query = filter(deviceData, query, queryStringParams, eqFields=['id'])

    # Perform query on `deviceData` table in database
    results = engine.connect().execute(query)

    # Query was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}
