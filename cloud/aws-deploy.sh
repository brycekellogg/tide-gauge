#!/bin/bash

# Publish cloud template and Lambda function source to S3
LAMBDA_SOURCE=lambda-$(uuidgen).zip
rm -rf lambda.zip
zip lambda.zip lambda.py
aws s3 cp cloud.yaml s3://tide-project
aws s3 cp lambda.zip s3://tide-project/$LAMBDA_SOURCE

aws cloudformation create-stack --stack-name tide-gauge \
                                --template-body file://cloud.yaml \
                                --capabilities CAPABILITY_IAM \
                                --parameters ParameterKey=LambdaSource,ParameterValue=$LAMBDA_SOURCE \
                                             ParameterKey=DeviceID,ParameterValue=${PARTICLE_DEVICE} \
                                             ParameterKey=ParticleToken,ParameterValue=${PARTICLE_TOKEN}
