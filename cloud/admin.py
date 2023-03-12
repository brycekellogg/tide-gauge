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


# A helper function that checks if a given stack exists.
#
# We can know if a given CloudFormation stack exists by
# attempting to describe it using boto3. If the stack
# does not exist, it will throw an exception. If the
# stack does exist, the describe operation will succeed.
#
# Params:
#    stackName = the name of the stack
#
# Returns:
#    True if the stack exists,
#    False if the stack does not exist,
#    None if we encounter an unexpected boto3 error.
#
def helper_stackExists(stackName):

#
#
#
def helper_templateValid(templateFilename):
    client = boto3.client('cloudformation')

    # Validate the we can read the template file
    if not os.access(templateFilename, os.R_OK):
        print(f"Error: could not read template file {templateFilename}")
        return False

    # We pass the template body as a string to all
    # future functions, so we read it in here.
    with open(templateFilename) as f:
        templateBody = f.read()

    # Validate the template itself via CloudFormation. If we don't
    # get an exception here, it means the tamplate is valid.
    try:
        res = client.validate_template(TemplateBody=templateBody)
    except ClientError as e:
        print(f"Error: {e.response['Error']['Message']}")
        return False

    return True


# A helper function that retrieves a list of stack resources
#
# Params:
#    stackName = the name of the stack
#
# Returns: a list of tuples where each item in the list
#          represents an individual resource. The tuples
#          are of the form (ResourceType, ResourceName)
#
def helper_stackResources(stackName):
    client = boto3.client('cloudformation')

    # Describe the stack resources using boto3 and parse the response.
    # Boto3 throws exceptions in certain cases, including when
    # a requested CloudFormation stack is not found.
    try:
        res = client.describe_stack_resources(StackName=stackName)
    except ClientError as e:
        print(f"Error: unexpected error: {e}")
        return None

    info = []
    for resource in res['StackResources']:
        info.append((resource['ResourceType'], resource['LogicalResourceId']))

    return info

#
#
#
#
def helper_deleteStack(stackName):
    client = boto3.client('cloudformation')

    # Describe the stack resources using boto3 and parse the response.
    # Boto3 throws exceptions in certain cases, including when
    # a requested CloudFormation stack is not found.
    try:
        res = client.delete_stack(StackName=stackName)
    except ClientError as e:
        print(f"Error: unexpected error: {e}")
        return None

    # Wait for stack deletion to complete
    waiter = client.get_waiter('stack_delete_complete')
    waiter.wait(StackName=stackName)

#
#
#
def command_awsDeploy(args):
    """

    Params:
       args.name = the name of the CloudFormation stack
       args.template = ???

    """
    stackName = args.name
    templateFilename = args.template

    cloudformation = boto3.client('cloudformation')
    s3 = boto3.client('s3')

    # Validate that the to-deploy stack does not already exist


    # Describe the stack using boto3 and parse the response.
    # Boto3 throws exceptions in certain cases, including when
    # a requested CloudFormation stack is not found.
    try:
        res = client.describe_stacks(StackName=stackName)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationError':
            return False # ValidationError means stack not found
        else:
            print(f"Error: unexpected error: {e}")
            return None
    return True




    # res = helper_stackExists(stackName)
    # if res is None:
    #     sys.exit()
    # elif res == True:
    #     sys.exit(f"Error: stack {stackName} already exists")

    # Validate the template exists, is readable, and is correct
    # if not helper_templateValid(templateFilename):
    #     sys.exit(f"Error: invalid template {templateFilename}")



    # TODO: create S3 bucket
    bucketName = f'{stackName}-{uuid.uuid4()}'
    res = s3.create_bucket(Bucket=bucketName, CreateBucketConfiguration={
        'LocationConstraint': 'us-west-2',
    },)
    # TODO: check result


    # TODO: upload template
    with open(templateFilename) as f :
        res = s3.put_object(ACL='public-read', Bucket=bucketName, Body=f.read(), Key='template.yaml')

    # TODO: zip and upload python
    # TODO: read in zipfile and upload it
    with zipfile.ZipFile('lambda.zip', mode='w') as archive:
        archive.write('lambda.py')
    with open('lambda.zip', 'rb') as f:
        res = s3.put_object(ACL='public-read', Bucket=bucketName, Body=f.read(), Key='lambda.zip')

    # Create the stack
    cloudformation.create_stack(
            StackName=stackName,
            TemplateURL=f'https://s3.amazonaws.com/{bucketName}/template.yaml',
            Capabilities=['CAPABILITY_NAMED_IAM'],
            Parameters=[
                {
                    'ParameterKey': 'LambdaBucket',
                    'ParameterValue': bucketName,
                }
                ])

    # Wait for stack creation to complete
    waiter = cloudformation.get_waiter('stack_create_complete')
    waiter.wait(StackName=stackName)

    # TODO: check that it was a success

    # TODO: delete bucket
    res = s3.delete_objects(
        Bucket=bucketName,
        Delete={'Objects': [
            {'Key': 'template.yaml',},
            {'Key': 'lambda.zip',},],
        },
    )
    res = s3.delete_bucket(Bucket=bucketName)



#
#
def update(args):
    pass


# Deletes a CloudFormation stack.
#
# If the stack with the given name exists, this
# command function will ask for confirmation, then
# delete the stack.
#
# Params:
#    stackName = the name of the stack to delete
#
def command_awsDelete(args):
    stackName = args.name

    # Validate that the to-delete stack exists
    res = helper_stackExists(stackName)
    if res is None:    sys.exit()
    elif res == False: sys.exit(f"Error: stack {stackName} does not exist")

    # Get a list of stack resources that will be deleted
    res = helper_stackResources(stackName)
    if res is None: sys.exit()

    # Print them out and get confirmation
    print(f"Deleting stack {stackName} with the following resources:")
    for resource in res:
        print(f"\t{resource[0]:<40}  {resource[1]:<25}")

    res = input("Continue? [y/N] ")
    if res != 'y':
        sys.exit("Cancelling delete")

    # Do the delete
    helper_deleteStack(stackName)

    # TODO: delete API keys
    client = boto3.client('apigateway')
    res = client.get_api_keys(nameQuery=args.name)
    for key in res['items']:
        keyId = key['id']
        res = client.delete_api_key(apiKey=keyId)

    print("Delete complete")


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



if __name__ == '__main__':
    DEFAULT_STACKNAME = 'tide-guage'

    argsParser = argparse.ArgumentParser()
    subParser = argsParser.add_subparsers()

    # The aws-deploy command
    parser_awsDeploy = subParser.add_parser('aws-deploy', help="Deploy AWS CloudFormation stack")
    parser_awsDeploy.add_argument('--name', default=DEFAULT_STACKNAME)
    parser_awsDeploy.add_argument('--template', default='template.yaml')
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

