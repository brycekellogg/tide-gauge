# Compile the firmware using the cloud compile
tide-gauge.bin: firmware/tide-gauge.ino
	@particle compile --target 2.0.0 --saveTo $@ boron

# Flash the bin to the device over USB
firmware-flash: tide-gauge.bin
	@particle usb dfu
	@particle flash --usb $?

# Program the device via a cloud OTA
firmware-ota: tide-gauge.bin
	@particle flash --cloud tide-gauge-1 tide-gauge.bin


webhook-deploy: cloud/webhook-sensor-data.json cloud/webhook-device-data.json
	@particle webhook create cloud/webhook-sensor-data.json
	@particle webhook create cloud/webhook-device-data.json


clean:
	rm -rf tide-gauge.bin
