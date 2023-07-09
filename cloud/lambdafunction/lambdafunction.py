#  _______ _     _         _____
# |__   __(_)   | |       / ____|
#    | |   _  __| | ___  | |  __  __ _ _   _  __ _  ___
#    | |  | |/ _` |/ _ \ | | |_ |/ _` | | | |/ _` |/ _ \
#    | |  | | (_| |  __/ | |__| | (_| | |_| | (_| |  __/
#    |_|  |_|\__,_|\___|  \_____|\__,_|\__,_|\__, |\___|
#                                             __/ |
#                                            |___/
# Author: Bryce Kellogg (bryce@kellogg.org)
# Copyright: 2023 Bryce Kellogg
# License: GPLv3
#
# 
import os
import json
import time
from pprint import pprint

import boto3

# We need the stack name to get a reference to the AWS
# DynamoDB table. We are assuming that the table name is
# of the form: "<stackName>-data-table". Cloudformation
# should have made the stack name available to the
# lambda function as an environment variable.

def process(event, context):
    """
    The main handler for the lambda function. Extracts the needed data
    from the HTTP event and calls one of the helper functions based on
    the path and HTTP method. If there is no match, return an error.
    """

    # Extract request data
    url = event['path']
    method = event['httpMethod']
    body = event['body']
    queryStringParams = event['queryStringParameters']



    # We load the JSON directly with the assumption that
    # it has already been validated. If there is an error,
    # the Python exception should result in an internal
    # server error being returned.
    # body = json.loads(body)

    # GET method on /data
    # /data?name=<id>&timestamp_eq=12&limit=100
    # /data?name=<id>&timestamp_lt=12&limit=100
    if url == '/data' and method == 'GET':

        stackName = os.environ['StackName']

        # Get the two required things and
        # delete them to make processing easier
        deviceName = queryStringParams['name']
        limit = queryStringParams['limit']
        del queryStringParams['name']
        del queryStringParams['limit']

        # The only remaining supported query
        # parameter is the 'timestamp_*' param.
        timestampQuery = next(iter(queryStringParams))
        timestamp = queryStringParams[timestampQuery]

        # We use this to convert from query tring params to
        # the operator used in the dynamodb query.
        _, op = timestampQuery.split('_')
        op = {'eq': '=', 'lt': '<', 'gt': '>', 'lte': '<=', 'gte': '>='}[op]

        # Get the actual results from the helper function
        return getData(stackName, deviceName, timestamp, op, limit)

    # POST method on /data
    #
    # {
    #   name = '???',
    #   data = [
    #       [1234, {aaemra=aksmd, askmdla=alksdl}],
    #   ]
    #   
    #
    # }
    if url == '/data' and method == 'POST':

        body = json.loads(body)
        stackName = os.environ['StackName']
        deviceName = body['name']
        return postData(stackName, deviceName, body['data'])

    # GET method on /config
    if url == '/config' and method == 'GET':
        pass

    # If we make it here, something is wrong
    return {'statusCode': 400, 'body': 'Bad Request'}


def getData(stackName, deviceName, timestamp, op, limit):
    """

    Params:
       stackName = The name of the CloudFormation stack
                   that the desired table is a part of.
       deviceName = The name of the device to get data from
       timestamp = The timestamp to use when querying data. This is
                   in the format of the number of seconds since
                   00:00:00 UTC on 1 January 1970 (Unix Time)
       op = The operation to apply to the timestamp. This can be one
            of ('=', '<', '>', '<=', '>=').
       limit = the number of records to be returned. Note that less than
               the limit may be returned.

    Returns: ???
    """

    # TODO: Validate Inputs

    # Make query to database table
    res = boto3.client('dynamodb').query(
            TableName=f'{stackName}-data-table',
            Limit=limit,
            ScanIndexForward=op in ['>', '>='],
            KeyConditionExpression=f'#devicename = :devicename AND #timestamp {op} :timestamp',
            ExpressionAttributeNames={
                '#timestamp': 'timestamp',
                '#devicename': 'devicename'
            },
            ExpressionAttributeValues={
                ':devicename': {'S': deviceName},
                ':timestamp':  {'N': str(timestamp)},
            },
        )

    # Format data for response
    data = []
    for attributes in res['Items']:
        # The two keys are always returned
        deviceName = str(attributes.pop('devicename')['S'])
        timestamp  = int(attributes.pop('timestamp')['N'])
        item = {'devicename': deviceName, 'timestamp': timestamp}

        # All other attributes are retreived, all as strings
        for k,v in attributes.items(): item[k] = v['S']
        data.append(item)

    return {'statusCode': 200, 'body': json.dumps(data)}


def postData(stackName, deviceName, dataList):
    """
    A helper function that saves sensor data to the AWS database.
    The param "body" is expected to be a string of JSON of the form
    desribed in the README.md.

    The string is assumed to already have been validated to conform
    to the input schema by AWS API Gateway. The contents of the JSON
    object are written to the AWS DynamoDB database each element in
    each metric becomes a single database record.

    Params:
        dataList = [(timestamp, {k,v}), ]

    """

    # Get config data
    res = boto3.client('dynamodb').query(
            TableName=f'{stackName}-config-table',
            KeyConditionExpression=f'#devicename = :devicename',
            ExpressionAttributeNames={'#devicename': 'devicename'},
            ExpressionAttributeValues={':devicename': {'S': deviceName}},
        )

    pprint(res)


    # The structure of the JSON allows us to iterate over all
    # the metrics one by one and batch write all the new data.
    # If there's an error, Python should throw an exception and
    # we'll return an internal server error.
    table = boto3.resource('dynamodb').Table(f'{stackName}-data-table')
    with table.batch_writer() as batch:
        for timestamp, attributes in dataList:
            item={'devicename': deviceName, 'timestamp': timestamp}
            for k,v in attributes.items():
                item[k] = str(v)  # must be string because floats not supported
            batch.put_item(Item=item)

    # Data write was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def deleteData(stackName, keyList):
    """

    """
    table = boto3.resource('dynamodb').Table(f'{stackName}-data-table')
    with table.batch_writer() as batch:
        for deviceName, timestamp in keyList:
            item={'devicename': deviceName, 'timestamp': timestamp}
            batch.delete_item(Key=item)

    # Delete was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def getConfig(stackName, deviceName = None):
    """

    """
    # TODO: Validate Inputs

    if deviceName:

        # Make query to database table
        res = boto3.client('dynamodb').query(
                TableName=f'{stackName}-config-table',
                KeyConditionExpression=f'#devicename = :devicename',
                ExpressionAttributeNames={'#devicename': 'devicename'},
                ExpressionAttributeValues={':devicename': {'S': deviceName}},
            )
    else:
        res = boto3.client('dynamodb').scan(TableName=f'{stackName}-config-table')

    # Format data for response
    data = []
    for attributes in res['Items']:
        # The two keys are always returned
        item = {}

        # All other attributes are retreived, all as strings
        for k,v in attributes.items(): item[k] = v['S']
        data.append(item)

    return {'statusCode': 200, 'body': json.dumps(data)}


def postConfig(stackName, deviceName, attributes):
    """

    """
    # The structure of the JSON allows us to iterate over all
    # the metrics one by one and batch write all the new data.
    # If there's an error, Python should throw an exception and
    # we'll return an internal server error.
    table = boto3.resource('dynamodb').Table(f'{stackName}-config-table')
    with table.batch_writer() as batch:
            item={'devicename': deviceName}
            for k,v in attributes.items():
                item[k] = str(v)  # must be string because floats not supported
            batch.put_item(Item=item)

    # Data write was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


def deleteConfig(stackName, deviceName):
    """

    """
    table = boto3.resource('dynamodb').Table(f'{stackName}-config-table')
    with table.batch_writer() as batch:
        batch.delete_item(Key={'devicename': deviceName})

    # Delete was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


