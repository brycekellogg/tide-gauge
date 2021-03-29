#!/bin/bash

# Publish cloud template and Lambda function source to S3
LAMBDA_SOURCE=lambda-$(uuidgen).zip
rm -rf lambda.zip lambda-dir/
mkdir lambda-dir
pip install -t lambda-dir -r requirements.txt --no-deps
cp lambda.py lambda-dir/
(cd lambda-dir; zip -r ../lambda.zip *)
aws s3 rm s3://${AWS_BUCKET}/ --recursive --exclude "*" --include "*.zip"
aws s3 cp cloud.yaml s3://${AWS_BUCKET}
aws s3 cp lambda.zip s3://${AWS_BUCKET}/$LAMBDA_SOURCE

aws cloudformation update-stack --stack-name tide-gauge \
                                --template-body file://cloud.yaml \
                                --capabilities CAPABILITY_IAM \
                                --parameters ParameterKey=LambdaSource,ParameterValue=$LAMBDA_SOURCE \
                                             ParameterKey=DeviceID,ParameterValue=${PARTICLE_DEVICE} \
                                             ParameterKey=ParticleToken,ParameterValue=${PARTICLE_TOKEN} \
                                             ParameterKey=BucketName,ParameterValue=${AWS_BUCKET}
