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

DEFAULT_STACKNAME = 'tide-guage'
DEFAULT_REGION = 'us-west-2'

if __name__ == '__main__':

    argsParser = argparse.ArgumentParser()
    subParser = argsParser.add_subparsers()

    # The aws-deploy command
    parser_awsDeploy = subParser.add_parser('aws-deploy', help="Deploy AWS CloudFormation stack")
    parser_awsDeploy.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_awsDeploy.add_argument('--region', default=DEFAULT_REGION)
    parser_awsDeploy.set_defaults(func=command_awsDeploy)

    # The aws-delete command
    parser_awsDelete = subParser.add_parser('aws-delete', help="Delete AWS CloudFormation stack")
    parser_awsDelete.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_awsDelete.set_defaults(func=command_awsDelete)

    # The aws-update command
    parser_awsUpdate = subParser.add_parser('aws-update')

    # The aws-apikey command
    parser_awsApikey = subParser.add_parser('aws-apikey', help="Manage AWS API Keys")
    parser_awsApikey.add_argument('--name', default=DEFAULT_STACKNAME)
    group_awsApikey = parser_awsApikey.add_mutually_exclusive_group()
    group_awsApikey.add_argument('--list', action='store_true')
    group_awsApikey.add_argument('--new',  action='store')
    group_awsApikey.add_argument('--remove',  action='store')
    parser_awsApikey.set_defaults(func=command_awsApikey)

    args = argsParser.parse_args()
    args.func(args)

