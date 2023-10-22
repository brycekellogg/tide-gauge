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

clean:
	@rm -rf firmware/tide-gauge.bin
