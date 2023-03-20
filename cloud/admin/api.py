#!/usr/bin/env python
#
# Actions:
#     - deploy (create or update)
#     - delete
#     - download data
#     - clear data
#     - archive data
#     - 
#
#
#
import sys
import os
import zipfile
import uuid
import argparse
import boto3
from pprint import pprint
from botocore.exceptions import ClientError

# Command handler for the aws-apikey command.
#
# Note: API keys are prefaced by the stack name in AWS.
#       When displayed here (or used as arguments) the
#       stack name is ommitted.
#
# Params:
#    args.name = the name of the CloudFormation stack
#    args.list = lists the registered API keys if True
#    args.new  = if not None, the name of the API key to create
#    args.remove = if not None, the name of the API key to delete
#
def command_awsApikey(args):
    stackName = args.name
    client = boto3.client('apigateway')

    # ???
    # ???
    if args.remove:
        # TODO: confirm
        # TODO: change to using name instead of ID

        res = client.delete_api_key(apiKey=args.remove)
        print(f"API Key {args.remove} deleted")

    # ???
    # ???
    if args.new:
        # TODO: check if name already exists
        # TODO: set to enabled on create
        res = client.create_api_key(name=f'{args.name}-{args.new}', enabled=True)

        keyId = res['id']

        # We need the ID of the usage plan to assign the API key to
        res = client.get_usage_plans()
        for plan in res['items']:
            if plan['name'] == args.name:
                usagePlanId = plan['id']
                break
        else:
            # TODO: delete the API key on error
            sys.exit(f"Error: usage plan '{args.name}' not found")

        #TODO: needs to be added to the usage plan
        res = client.create_usage_plan_key(
                usagePlanId=usagePlanId,
                keyId=keyId,
                keyType='API_KEY')
        print(res)

    # ???
    # ???
    if args.list:
        res = client.get_api_keys(nameQuery=args.name)
        print("Current API Keys:")
        # TODO: better print if there's none
        # TODO: print header
        # TODO: print value
        for key in res['items']:
            print(f"\t{key['id']:<10}\t{key['name'].replace(stackName+'-', ''):<25}\t{key['createdDate']}")

