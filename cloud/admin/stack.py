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
import sys
import os
import io
from zipfile import ZipFile
import uuid
import boto3
from pprint import pprint
from botocore.exceptions import ClientError


def command_awsDeploy(args):
    """
    The function for creating/deploying the CloudFormation stack.

    The process for deploying the stack consists of:
       - validating inputs & templates
       - creating an S3 bucket
       - uploading template files to the S3 bucket
       - zipping the lambda function code
       - uploading the zipfile to the S3 bucket
       - creating the stack
       - cleaning up & deleting the S3 bucket

    Params:
       args.name = the name of the CloudFormation stack
       args.region = the AWS region this stack will be deployed in
    """
    stackName = args.name
    region = args.region

    # Filenames for the various files that need to be uploaded
    topLevelTemplateFilename = 'templates/template.yaml'
    databaseTemplateFilename = 'templates/template-db.yaml'
    apiGatewayTemplateFilename = 'templates/template-api.yaml'
    lambdaTemplateFilename = 'templates/template-lambda.yaml'
    lambdaFilename = 'lambda.py'
    lambdaZipFilename = 'lambda.zip'

    # Pre-declare boto3 clients needed to deploy
    cloudformation = boto3.client('cloudformation')
    s3 = boto3.client('s3')

    # Validate that the to-deploy stack does not already exist. Describe the stack
    # using boto3 and expect it to throw a ClientError with code "ValidationError".
    try:
        res = cloudformation.describe_stacks(StackName=stackName)
    except ClientError as e:
        if e.response['Error']['Code'] != 'ValidationError':
            sys.exit(f"Error: unexpected error describing stack {e}")
    else:
        sys.exit(f"Error: stack {stackName} already exists")

    # Validate each template exists, is readable, and is valid
    if not os.access(topLevelTemplateFilename, os.R_OK):   sys.exit(f"Error: could not read template file {topLevelTemplateFilename}")
    if not os.access(databaseTemplateFilename, os.R_OK):   sys.exit(f"Error: could not read template file {databaseTemplateFilename}")
    if not os.access(apiGatewayTemplateFilename, os.R_OK): sys.exit(f"Error: could not read template file {apiGatewayTemplateFilename}")
    if not os.access(lambdaTemplateFilename, os.R_OK):     sys.exit(f"Error: could not read template file {lambdaTemplateFilename}")

    # We pass the template body as a string to multiple future functions, so we read it in here.
    with open(topLevelTemplateFilename)   as f: topLevelTemplateBody   = f.read()
    with open(databaseTemplateFilename)   as f: databaseTemplateBody   = f.read()
    with open(apiGatewayTemplateFilename) as f: apiGatewayTemplateBody = f.read()
    with open(lambdaTemplateFilename)     as f: lambdaTemplateBody     = f.read()

    # Zip the python file of the lambda function into an in-memory zipfile
    zipBuffer = io.BytesIO()
    with ZipFile(zipBuffer, mode='a') as archive: archive.write(lambdaFilename)

    # Validate the template itself via CloudFormation. If we don't
    # get an exception here, it means the tamplate is valid.
    try:
        cloudformation.validate_template(TemplateBody=topLevelTemplateBody)
        cloudformation.validate_template(TemplateBody=databaseTemplateBody)
        cloudformation.validate_template(TemplateBody=apiGatewayTemplateBody)
        cloudformation.validate_template(TemplateBody=lambdaTemplateBody)
    except ClientError as e:
        sys.exit(f"Error: {e.response['Error']['Message']}")

    # Create an S3 bucket to store CloudFormation template files & lambda function code in
    bucketName = f'{stackName}-{uuid.uuid4()}'
    bucketConfiguration = {'LocationConstraint': region}
    try:
        s3.create_bucket(Bucket=bucketName, CreateBucketConfiguration=bucketConfiguration)
    except ClientError as e:
        sys.exit(f"Error: unexpected error creating bucket {e}")

    # Upload all the CloudFormation templates to the AWS S3 bucket
    try:
        s3.put_object(ACL='public-read', Bucket=bucketName, Body=topLevelTemplateBody,   Key=topLevelTemplateFilename)
        s3.put_object(ACL='public-read', Bucket=bucketName, Body=databaseTemplateBody,   Key=databaseTemplateFilename)
        s3.put_object(ACL='public-read', Bucket=bucketName, Body=apiGatewayTemplateBody, Key=apiGatewayTemplateFilename)
        s3.put_object(ACL='public-read', Bucket=bucketName, Body=lambdaTemplateBody,     Key=lambdaTemplateFilename)
        s3.put_object(ACL='public-read', Bucket=bucketName, Body=zipBuffer.getvalue(),   Key=lambdaZipFilename)
    except ClientError as e:
        sys.exit(f"Error: unexpected error uploading templates {e}")  # TODO: may leak S3 bucket

    # Create the stack itself
    topLevelTemplateURL   = f'https://s3.amazonaws.com/{bucketName}/{topLevelTemplateFilename}'
    databaseTemplateURL   = f'https://s3.amazonaws.com/{bucketName}/{databaseTemplateFilename}'
    apiGatewayTemplateURL = f'https://s3.amazonaws.com/{bucketName}/{apiGatewayTemplateFilename}'
    lambdaTemplateURL     = f'https://s3.amazonaws.com/{bucketName}/{lambdaTemplateFilename}'
    parameters = [
        {'ParameterKey': 'databaseTemplateURL',   'ParameterValue': databaseTemplateURL},
        {'ParameterKey': 'apiGatewayTemplateURL', 'ParameterValue': apiGatewayTemplateURL},
        {'ParameterKey': 'lambdaTemplateURL',     'ParameterValue': lambdaTemplateURL},
    ]
    cloudformation.create_stack(
            StackName=stackName,
            TemplateURL=topLevelTemplateURL,
            Capabilities=['CAPABILITY_NAMED_IAM'],
            Parameters=parameters)

    # Wait for stack creation to complete & continue to cleanup even if it fails
    try:
        waiter = cloudformation.get_waiter('stack_create_complete')
        waiter.wait(StackName=stackName)
    except ClientError as e:
        print(f"Error: unexpected error deploying {e}")

    # Clean up deploy by deleting S3 bucket
    toDeleteObjects = [
        {'Key': topLevelTemplateFilename},
        {'Key': databaseTemplateFilename},
        {'Key': apiGatewayTemplateFilename},
        {'Key': lambdaTemplateFilename},
        {'Key': lambdaZipFilename},
    ]
    try:
        s3.delete_objects(Bucket=bucketName, Delete={'Objects': toDeleteObjects})
        s3.delete_bucket(Bucket=bucketName)
    except ClientError as e:
        sys.exit(f"Error: unexpected error cleaning up bucket {e}")


def update(args):
    pass


def command_awsDelete(args):
    """
    Deletes a CloudFormation stack.

    If the stack with the given name exists, this
    command function will ask for confirmation, then
    delete the stack.

    Params:
       stackName = the name of the stack to delete

    """
    stackName = args.name

    cloudformation = boto3.client('cloudformation')
    apigateway = boto3.client('apigateway')

    # Validate that the to-deploy stack does indeed exist.
    # Describe the stack using boto3 and expect it to not
    # throw any exceptions.
    try:
        res = cloudformation.describe_stacks(StackName=stackName)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationError':
            sys.exit(f"Error: stack {stackName} does not exist")
        else:
            sys.exit(f"Error: unexpected error describing stack {e}")

    # Get a list of stack resources that will be deleted
    res = helper_stackResources(stackName)
    if res is None: sys.exit()

    # TODO: recursively print out substack resources

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
    res = apigateway.get_api_keys(nameQuery=args.name)
    for key in res['items']:
        keyId = key['id']
        res = apigateway.delete_api_key(apiKey=keyId)


    print("Delete complete")

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

