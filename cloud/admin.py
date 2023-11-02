#!/usr/bin/env python
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
import argparse
from admin import *
from lambdafunction import *

DEFAULT_STACKNAME = 'tide-guage'
DEFAULT_REGION = 'us-west-2'

if __name__ == '__main__':

    argsParser = argparse.ArgumentParser()
    subParser = argsParser.add_subparsers()

    # The stack-deploy command
    parser_stackDeploy = subParser.add_parser('stack-deploy', help="Deploy AWS CloudFormation stack")
    parser_stackDeploy.set_defaults(func=command_stackDeploy)
    parser_stackDeploy.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_stackDeploy.add_argument('--region', default=DEFAULT_REGION)

    # The stack-delete command
    parser_stackDelete = subParser.add_parser('stack-delete', help="Delete AWS CloudFormation stack")
    parser_stackDelete.set_defaults(func=command_stackDelete)
    parser_stackDelete.add_argument('--name', default=DEFAULT_STACKNAME)

    # The stack-update command
    parser_stackUpdate = subParser.add_parser('stack-update', help="Update AWS Cloudformation stack")
    parser_stackUpdate.set_defaults(func=command_stackUpdate)
    parser_stackUpdate.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_stackUpdate.add_argument('--region', default=DEFAULT_REGION)

    # The db-data command
    parser_dbData = subParser.add_parser('db-data', help="Manage the data table")
    parser_dbData.set_defaults(func=command_dbData)
    parser_dbData.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_dbData.add_argument('--device', required=True)
    parser_dbData.add_argument('--timestamp')
    parser_dbData.add_argument('--limit', type=int)  # used in GET only
    parser_dbData.add_argument('--data')             # used in POST only
    # TODO: make mutually exclusive
    parser_dbData.add_argument('--post', action='store_true')
    parser_dbData.add_argument('--get', action='store_true')
    parser_dbData.add_argument('--delete', action='store_true')

    # The db-config command
    parser_dbConfig = subParser.add_parser('db-config', help="Manage the config table")
    parser_dbConfig.set_defaults(func=command_dbConfig)
    parser_dbConfig.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_dbConfig.add_argument('--device')
    parser_dbConfig.add_argument('--data')             # used in POST only
    parser_dbConfig.add_argument('--post', action='store_true')
    parser_dbConfig.add_argument('--get', action='store_true')
    parser_dbConfig.add_argument('--delete', action='store_true')

    # TODO: The lambda-invoke command
    parser_lambdaInvoke = subParser.add_parser('lambda-invoke', help="Call the lambda function")
    parser_lambdaInvoke.set_defaults(func=command_lambdaInvoke)
    parser_lambdaInvoke.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_lambdaInvoke.add_argument('--device')
    parser_lambdaInvoke.add_argument('--timestamp')
    parser_lambdaInvoke.add_argument('--limit', type=int)  # used in GET only
    parser_lambdaInvoke.add_argument('--data')             # used in POST only
    # TODO: make mutually exclusive
    parser_lambdaInvoke.add_argument('--post', action='store_true')
    parser_lambdaInvoke.add_argument('--get', action='store_true')
    parser_lambdaInvoke.add_argument('--config', action='store_true')

    # The aws-apikey command
    parser_awsApikey = subParser.add_parser('aws-apikey', help="Manage AWS API Keys")
    parser_awsApikey.set_defaults(func=command_awsApikey)
    parser_awsApikey.add_argument('--name', default=DEFAULT_STACKNAME)
    group_awsApikey = parser_awsApikey.add_mutually_exclusive_group()
    group_awsApikey.add_argument('--list', action='store_true')
    group_awsApikey.add_argument('--new',  action='store')
    group_awsApikey.add_argument('--remove',  action='store')



    args = argsParser.parse_args()
    args.func(args)

