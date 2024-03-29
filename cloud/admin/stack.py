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
from urllib import request
import boto3
from pprint import pprint
from botocore.exceptions import ClientError


def command_stackDeploy(args):
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
    templateFilename = 'templates/template.yaml'
    lambdaFilename = 'lambdafunction/lambdafunction.py'
    lambdaArcname = 'lambdafunction.py'
    lambdaZipFilename = f'lambda-{uuid.uuid4()}.zip'

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
    if not os.access(templateFilename, os.R_OK):
        sys.exit(f"Error: could not read template file {templateFilename}")

    # We pass the template body as a string to multiple future functions, so we read it in here.
    with open(templateFilename) as f:
        templateBody = f.read()

    # Zip the python file of the lambda function into an in-memory zipfile
    zipBuffer = io.BytesIO()
    with ZipFile(zipBuffer, mode='a') as archive: archive.write(lambdaFilename, arcname=lambdaArcname)

    # Validate the template itself via CloudFormation. If we don't
    # get an exception here, it means the tamplate is valid.
    try:
        cloudformation.validate_template(TemplateBody=templateBody)
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
        s3.put_object(Bucket=bucketName, Body=templateBody,         Key=templateFilename)
        s3.put_object(Bucket=bucketName, Body=zipBuffer.getvalue(), Key=lambdaZipFilename)
    except ClientError as e:
        # TODO: clean up AWS S3 bucket
        sys.exit(f"Error: unexpected error uploading templates {e}")  # TODO: may leak S3 bucket

    # Create the stack itself
    templateURL = f'https://s3.amazonaws.com/{bucketName}/{templateFilename}'
    parameters = [
        {'ParameterKey': 'bucketName',  'ParameterValue': bucketName},
        {'ParameterKey': 'zipfileName', 'ParameterValue': lambdaZipFilename},
    ]
    cloudformation.create_stack(
            StackName=stackName,
            TemplateURL=templateURL,
            Capabilities=['CAPABILITY_NAMED_IAM'],
            Parameters=parameters)

    # Wait for stack creation to complete & continue to cleanup even if it fails
    try:
        waiter = cloudformation.get_waiter('stack_create_complete')
        waiter.wait(StackName=stackName)
    except ClientError as e:
        print(f"Error: unexpected error deploying {e}")



def command_stackUpdate(args):
    """
    The function for updating an existing stack.

    Params:
        args.name = the name of the CloudFormation stack
    """
    stackName = args.name

    # Filenames for the various files that need to be uploaded
    templateFilename = 'templates/template.yaml'
    lambdaFilename = 'lambdafunction/lambdafunction.py'
    lambdaArcname = 'lambdafunction.py'
    lambdaZipFilename = f'lambda-{uuid.uuid4()}.zip'

    # Pre-declare boto3 clients needed to update
    cloudformation = boto3.client('cloudformation')
    s3 = boto3.client('s3')
    lambdaClient = boto3.client('lambda')
    
    # Validate that the to-update stack does already exist. Describe the stack
    # using boto3 and expect it to throw a ClientError with code "ValidationError".
    try:
        res = cloudformation.describe_stacks(StackName=stackName)
    except ClientError as e:
        if e.response['Error']['Code'] != 'ValidationError':
            sys.exit(f"Error: unexpected error describing stack {e}")
        sys.exit(f"Error: stack {stackName} does not exists")

    # Get S3 bucket for stack
    bucketName = next(_ for _ in res['Stacks'][0]['Parameters'] if _['ParameterKey'] == 'bucketName')['ParameterValue']
    lambdaZipFileNameOld = next(_ for _ in res['Stacks'][0]['Parameters'] if _['ParameterKey'] == 'zipfileName')['ParameterValue']
    lambdaArn = next(_ for _ in res['Stacks'][0]['Outputs'] if _['OutputKey'] == 'lambdaArn')['OutputValue']

    # Validate each template exists, is readable, and is valid
    if not os.access(templateFilename, os.R_OK):
        sys.exit(f"Error: could not read template file {templateFilename}")

    # We pass the template body as a string to multiple future functions, so we read it in here.
    with open(templateFilename) as f:
        templateBody = f.read()
    with open(lambdaFilename) as f:
        lambdaBody = f.read()

    # Validate the template itself via CloudFormation. If we don't
    # get an exception here, it means the tamplate is valid.
    try:
        cloudformation.validate_template(TemplateBody=templateBody)
    except ClientError as e:
        sys.exit(f"Error: {e.response['Error']['Message']}")

    # Download existing lambda function python code
    res = lambdaClient.get_function(FunctionName=lambdaArn)
    lambdaUrl = res['Code']['Location']
    lambdaContents = io.BytesIO(request.urlopen(lambdaUrl).read())

    with ZipFile(lambdaContents) as archive:
        lambdaText = archive.read(lambdaArcname)
    lambdaUpdate = lambdaText.decode('utf-8') != lambdaBody
        
    if lambdaUpdate:
        # Zip the python file of the lambda function into an in-memory zipfile
        zipBuffer = io.BytesIO()
        with ZipFile(zipBuffer, mode='a') as archive: archive.write(lambdaFilename, arcname=lambdaArcname)
    else:
        lambdaZipFilename = lambdaZipFileNameOld


    # Upload all the CloudFormation templates to the AWS S3 bucket
    try:
        s3.put_object(Bucket=bucketName, Body=templateBody, Key=templateFilename)
        if lambdaUpdate:
            s3.put_object(Bucket=bucketName, Body=zipBuffer.getvalue(), Key=lambdaZipFilename)
            s3.delete_object(Bucket=bucketName, Key=lambdaZipFileNameOld)
    except ClientError as e:
        # TODO: clean up AWS S3 bucket
        sys.exit(f"Error: unexpected error uploading templates {e}")  # TODO: may leak S3 bucket


    # Create change set
    templateURL = f'https://s3.amazonaws.com/{bucketName}/{templateFilename}'
    parameters = [
        {'ParameterKey': 'bucketName',  'ParameterValue': bucketName},
        {'ParameterKey': 'zipfileName', 'ParameterValue': lambdaZipFilename},
    ]
    cloudformation.create_change_set(
            StackName=stackName,
            ChangeSetName='update',
            TemplateURL=templateURL,
            Capabilities=['CAPABILITY_NAMED_IAM'],
            Parameters=parameters)

    # Wait for change set to be fully defined
    waiter = cloudformation.get_waiter('change_set_create_complete')
    waiter.wait(
            StackName=stackName,
            ChangeSetName='update')

    res = cloudformation.describe_change_set(
            StackName=stackName,
            ChangeSetName='update')

    # Get confirmation
    changes = res['Changes']
    print(f"Updating stack {stackName} with the following changes:")
    for c in changes:
        print(f"\t{c['ResourceChange']['Action']:<40}  {c['ResourceChange']['ResourceType']:<25}")

    res = input("Continue? [y/N] ")
    if res != 'y':
        cloudformation.delete_change_set(
            StackName=stackName,
            ChangeSetName='update')
        sys.exit("Cancelling update")

    # Execute the change set
    res = cloudformation.execute_change_set(
            StackName=stackName,
            ChangeSetName='update')

    waiter = cloudformation.get_waiter('stack_update_complete')
    waiter.wait(StackName=stackName)





    

def command_stackDelete(args):
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

    # Clean up deploy by deleting S3 bucket
    # TODO: move this to "delete"
    # toDeleteObjects = [
    #     {'Key': topLevelTemplateFilename},
    #     {'Key': databaseTemplateFilename},
    #     {'Key': apiGatewayTemplateFilename},
    #     {'Key': lambdaTemplateFilename},
    #     {'Key': lambdaZipFilename},
    # ]
    # try:
    #     s3.delete_objects(Bucket=bucketName, Delete={'Objects': toDeleteObjects})
    #     s3.delete_bucket(Bucket=bucketName)
    # except ClientError as e:
    #     sys.exit(f"Error: unexpected error cleaning up bucket {e}")

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

