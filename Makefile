# Compile the firmware using the cloud compile
firmware/tide-gauge.bin: firmware/tide-gauge.ino
	@cd firmware && particle compile --target 2.0.0 --saveTo $(@F) boron

# Flash the bin to the device over USB
firmware-flash: firmware/tide-gauge.bin
	@particle usb dfu
	@particle flash --usb $?

# Program the device via a cloud OTA
firmware-ota: tide-gauge.bin
	@particle flash --cloud tide-gauge-1 tide-gauge.bin

# Update particle webhooks
webhook-deploy: cloud/webhook-sensor-data.json cloud/webhook-device-data.json
	@sed -e 's@AWS_APIKEY@'"${AWS_APIKEY}"'@' cloud/webhook-sensor-data.json > webhook-sensor-data.tmp.json
	@sed -e 's@AWS_APIKEY@'"${AWS_APIKEY}"'@' cloud/webhook-device-data.json > webhook-device-data.tmp.json
	@particle webhook delete all
	@particle webhook create webhook-sensor-data.tmp.json
	@particle webhook create cloud/webhook-device-data.tmp.json
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
aws-deploy: cloud/lambda.zip cloud/cloud.yaml
	@aws s3 rm s3://${AWS_BUCKET}/ --recursive --exclude "*" --include "*.zip"
	@aws s3 cp cloud/lambda.zip s3://${AWS_BUCKET}/${LAMBDA_SOURCE}
	@aws cloudformation update-stack --stack-name tide-gauge \
									 --template-body file://cloud/cloud.yaml \
									 --capabilities CAPABILITY_IAM \
									 --parameters ParameterKey=LambdaSource,ParameterValue=${LAMBDA_SOURCE} \
												  ParameterKey=DeviceID,ParameterValue=${PARTICLE_DEVICE} \
												  ParameterKey=ParticleToken,ParameterValue=${PARTICLE_TOKEN} \
												  ParameterKey=BucketName,ParameterValue=${AWS_BUCKET}

clean:
	@rm -rf firmware/tide-gauge.bin cloud/lambda.zip cloud/lambda-dir
