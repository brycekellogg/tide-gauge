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
#
import json
import boto3
import sys
from tabulate import tabulate

from pprint import pprint

def command_lambdaInvoke(args):
    """

    """
    stackName = args.name


    # We decide on the path based on the action
    path = None
    if args.post:   method, path = ('POST', '/data')
    if args.get:    method, path = ('GET', '/data')
    if args.config: method, path = ('GET', '/config')
    if path is None: sys.exit("ERROR: invalid action")

    # Build the event
    event = {
        'path': path,
        'httpMethod': method,
        'body': '',
        'queryStringParameters': []
    }

    # Extract the timestamp & operator from the argument. We're expecting to receive
    # it in the form "<10" but the URL query args need it in the format "timestamp_lt=10".
    if args.get:
        op = [_ for _ in ['<=', '>=', '=', '<', '>'] if _ in args.timestamp]
        if not op: sys.exit("ERROR: invalid or missing timestamp operator")
        op = next(iter(op))
        timestamp = args.timestamp.replace(op, '')
        op = {'=': 'eq', '<': 'lt', '>': 'gt', '<=': 'lte', '>=': 'gte'}[op]

    # What goes into the event depends on post, get, etc
    if args.post: event['body'] = args.data
    if args.get: event['queryStringParameters'] ={'name': args.device, 'limit': args.limit, f'timestamp_{op}': timestamp}
    if args.config: event['queryStringParameters'] = None

    # Make the actual invokation
    functionName = f"{stackName}-lambda-function"
    res = boto3.client('lambda').invoke(FunctionName=functionName,
                                        InvocationType='RequestResponse',
                                        Payload=json.dumps(event))

    # Parse the response if we did a GET operation
    if args.get:
        payload = res['Payload']
        data = json.loads(json.loads(payload.read())['body'])
        if len(data) == 0: return # skip printing or deleting if there's no data
        print(tabulate(data, headers='keys'))
    
    # Parse the response if we did a POST operation
    # if args.post:
        # pprint(res['Payload'].read())
