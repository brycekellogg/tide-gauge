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
# This file contains the command handlers for commands that
# directly interact with the DynamoDB database. Each command
# handler uses the functions from the AWS Lambda Function code
# to interact with the database and is responsible for
# formatting command inputs and lambda function outputs.
import sys
import json
from tabulate import tabulate
from collections import OrderedDict
from . import *

def command_dbData(args):
    """
    Command handler for interacting with the data table.

    This function processes the command inputs and uses the
    AWS Lambda Function code to read, write, & delete entries
    in the data table. The operation performed is controlled
    via the {args.get, args.post, args.delete} options. Other
    options are used to limit the queries.

    Timestamp Format: "<op><val>" where <op> is one of
                      {'=', '<', '>', '<=', '>='} and
                      <val> is a Unix timestamp.

    Data Format: "<key1>=<value1>;<key2>=<value2>;..." is a
                 set of key/value pairs, each pair separated
                 by a semicolon.

    Params:
       args.get = indicates a read operation
       args.post = indicates a write operation
       args.delete = indicates a delete operation
       args.name = the name of the CloudFormation stack to operate on
       args.device = the name of the device whose data to operate on
       args.timestamp = the timestamp query string
       args.limit = the maximum number of items to return or delete
       args.data = the data to post
    """
    stackName = args.name
    deviceName = args.device

    # Both GET & DELETE need to query data
    if args.get or args.delete:
        limit = args.limit

        # Parse the timestamp to get the operator & Unix timestamp
        op = [_ for _ in ['<=', '>=', '=', '<', '>'] if _ in args.timestamp]
        if not op: sys.exit("ERROR: invalid or missing timestamp operator")
        op = next(iter(op))
        timestamp = args.timestamp.replace(op, '')

        # Perform query using lambda function
        res = getData(stackName, deviceName, timestamp, op, limit)
        if res['statusCode'] != 200: sys.exit("ERROR: query error {res}")

        # Display returned data
        data = json.loads(res['body'])
        if len(data) == 0: return # skip printing or deleting if there's no data
        print(tabulate(data, headers='keys'))

    # Delete data after confirmation. Note that
    # we need to query data before deletion for
    # confirmation and to get the keys to delete.
    if args.delete:
        res = input("\nDelete above data? [y/N] ")
        if res != 'y': sys.exit("Cancelling delete")
        
        # Format keys to delete based on data read using GET
        keyList = []
        for item in data: keyList.append((item['devicename'], item['timestamp']))

        # Perform the deletion using lambda function code
        res = deleteData(stackName, keyList)
        if res['statusCode'] != 200: sys.exit("ERROR: query error {res}")
        
    # Insert or update data. In this case,
    # timestamp is an individual Unix Timestamp
    # and does not include an operator. Instead
    # it indicates the timestamp of the event.
    if args.post:
        timestamp = int(args.timestamp)
        attributes = {}
        for a in args.data.split(';'):
            k,v = a.split('=')
            attributes[k] = v

        # Insert data using lambda function code
        res = postData(stackName, deviceName, [(timestamp, attributes)])
        if res['statusCode'] != 200: sys.exit("ERROR: query error {res}")


def command_dbConfig(args):
    """
    Command handler for interacting with the config table.

    Params:
       args.name
       args.device
       args.data

    """
    stackName = args.name
    deviceName = args.device

    #
    if args.get or args.delete:

        res = getConfig(stackName, deviceName)
        if res['statusCode'] != 200: sys.exit("ERROR: query error {res}")

        # We want the devicename to the left of the table
        unorderedData = json.loads(res['body'])
        orderedData = []
        for _ in unorderedData:
            _ = OrderedDict(_)
            _.move_to_end('devicename', last=False)
            orderedData.append(_)

        # Display ordered data
        print(tabulate(orderedData, headers='keys'))

    # The the single config that corresponds
    # to the currently selected device.
    if args.delete:
        res = input("\nDelete above data? [y/N] ")
        if res != 'y': sys.exit("Cancelling delete")

        res = deleteConfig(stackName, deviceName)
        if res['statusCode'] != 200: sys.exit("ERROR: query error {res}")
        
    # Insert or update data
    if args.post:
        attributes = {}
        for a in args.data.split(';'):
            k,v = a.split('=')
            attributes[k] = v

        # Insert data using lambda function code
        res = postConfig(stackName, deviceName, attributes)
        if res['statusCode'] != 200: sys.exit("ERROR: query error {res}")

