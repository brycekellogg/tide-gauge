import os
import json
import boto3
import time

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

    # Call correct helper function based on path & method
    if url == '/data' and method == 'POST': return postData(body)
    if url == '/data' and method == 'GET':  return getData(queryStringParams)

    # If we make it here, something is wrong
    return {'statusCode': 400, 'body': 'Bad Request'}


def getData(queryParams):
    """

    query params:
       - id=???
       - metric=???
       - timestamp_op=???
          - op = [eq, lt, gt, lte, gte]
       - limit


    /data?id=<id>&metric=<metric>&timestamp_eq=12&limit=100
    /data?id=<id>&metric=<metric>&timestamp_lt=12&limit=100


    """

    # We need the stack name to get a reference to the AWS
    # DynamoDB table. We are assuming that the table name is
    # of the form: "<stackName>-data-table". Cloudformation
    # should have made the stack name available to the
    # lambda function as an environment variable.
    stackName = 'tide-guage' #os.environ['StackName']

    # Get the two required things and
    # delete them to make processing easier
    deviceID = queryParams['id']
    metric = queryParams['metric']
    limit = queryParams['limit']
    del queryParams['id']
    del queryParams['metric']
    del queryParams['limit']

    # The only remaining supported query
    # parameter is the 'timestamp_*' param.
    timestampQuery = next(iter(queryParams))
    timestamp = queryParams[timestampQuery]

    # We use this to convert from query tring params to
    # the operator used in the dynamodb query.
    _, op = timestampQuery.split('_')
    op = {'eq': '=', 'lt': '<', 'gt': '>', 'lte': '<=', 'gte': '>='}[op]

    res = boto3.client('dynamodb').query(
            TableName=f'{stackName}-data-table',
            Limit=limit,
            KeyConditionExpression=f'idmetric = :metric AND #timestamp {op} :timestamp',
            ExpressionAttributeNames={'#timestamp': 'timestamp'},
            ScanIndexForward=op in ['>', '>='],
            ExpressionAttributeValues={
                ':metric': {'S': f'{deviceID}-{metric}'},
                ':timestamp': {'N': str(timestamp)},
            }
        )

    data = []
    for item in res['Items']:
        timestamp = int(item['timestamp']['N'])
        value = float(item['value']['N'])
        data.append({'timestamp': timestamp, 'value': value})

    return {'statusCode': 200, 'body': json.dumps(data)}


def postData(body):
    """A helper function that saves sensor data to the AWS database.
       The param "body" is expected to be a string of JSON of the form
       desribed in the README.md.

       The string is assumed to already have been validated to conform
       to the input schema by AWS API Gateway. The contents of the JSON
       object are written to the AWS DynamoDB database each element in
       each metric becomes a single database record."""

    # We need the stack name to get a reference to the AWS
    # DynamoDB table. We are assuming that the table name is
    # of the form: "<stackName>-data-table". Cloudformation
    # should have made the stack name available to the
    # lambda function as an environment variable.
    stackName = os.environ['StackName']

    # We load the JSON directly with the assumption that
    # it has already been validated. If there is an error,
    # the Python exception should result in an internal
    # server error being returned.
    body = json.loads(body)

    # Each request should have a single device ID
    # associated with it. We extract it here and
    # assume it applies to all contained records.
    deviceID = body['id']

    # The structure of the JSON allows us to iterate over all
    # the metrics one by one and batch write all the new data.
    # If there's an error, Python should throw an exception and
    # we'll return an internal server error.
    table = boto3.resource('dynamodb').Table(f'{stackName}-data-table')
    with table.batch_writer() as batch:
        for metric, valueList in body['data'].items():
            for value in valueList:
                item={'id-metric': f'{deviceID}-{metric}',
                      'timestamp': value['timestamp'],
                      'value': str(value['value'])}  # must be string because floats not supported
                batch.put_item(Item=item)

    # Data write was a success, return success code
    return {'statusCode': 200, 'body': 'OK'}


if __name__ == '__main__':
    queryParams = {
        'id': 'test',
        'metric': 'distance',
        'limit': 2,
        'timestamp_lte': 2
    }
    getData(queryParams)



