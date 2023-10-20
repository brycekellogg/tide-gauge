PARTICLE=${HOME}/.local/bin/particle

# Compile the firmware using the cloud compile
firmware/tide-gauge.bin: firmware/tide-gauge.ino
	@cd firmware && ${PARTICLE} compile --target 2.0.0 --saveTo $(@F) boron

# Flash the bin to the device over USB
firmware-flash: firmware/tide-gauge.bin
	@${PARTICLE} usb dfu
	@${PARTICLE} flash --usb $?

# Program the device via a cloud OTA
firmware-ota: firmware/tide-gauge.bin
	@${PARTICLE} flash --cloud tide-gauge-1 $?

# Update ${PARTICLE} webhooks
webhook-deploy: cloud/webhook-sensor-data.json
	@sed -e 's@AWS_APIKEY@'"${AWS_APIKEY}"'@' cloud/webhook-sensor-data.json > webhook-sensor-data.tmp.json
	@${PARTICLE} webhook delete all
	@${PARTICLE} webhook create webhook-sensor-data.tmp.json
	@rm *.tmp.json

# Build the zip file with code for lambda function
cloud/lambda.zip: cloud/lambda.py cloud/requirements.txt
	@rm -rf cloud/lambda.zip cloud/lambda-dir/
	@mkdir cloud/lambda-dir
	@pip install -t cloud/lambda-dir -r cloud/requirements.txt --no-deps
	@cp cloud/lambda.py cloud/lambda-dir/
	@(cd cloud/lambda-dir; zip -r ../lambda.zip *)

# Upload everything to S3 and update stack
LAMBDA_SOURCE:=lambda-$(shell uuidgen).zip
aws-deploy: cloud/cloud.yaml
	# @aws s3 cp cloud/lambda.zip s3://${AWS_BUCKET}/${LAMBDA_SOURCE}
	@aws cloudformation create-stack --stack-name tide-gauge \
									 --template-body file://cloud/cloud.yaml \
									 --capabilities CAPABILITY_IAM \
									 --parameters ParameterKey=LambdaSource,ParameterValue=${LAMBDA_SOURCE} \
												  ParameterKey=DeviceID,ParameterValue=${PARTICLE_DEVICE} \
												  ParameterKey=ParticleToken,ParameterValue=${PARTICLE_TOKEN} \
												  ParameterKey=BucketName,ParameterValue=${AWS_BUCKET}
	@aws cloudformation wait stack-update-complete --stack-name tide-gauge

clean:
	@rm -rf firmware/tide-gauge.bin cloud/lambda.zip cloud/lambda-dir
