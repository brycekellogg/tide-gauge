# Compile the firmware using the cloud compile
tide-gauge.bin: tide-gauge.ino
	@particle compile --target 2.0.0 --saveTo tide-gauge.bin boron

# Flash the bin to the device over USB
flash: tide-gauge.bin
	@particle flash --usb tide-gauge.bin

# Program the device via a cloud OTA
ota: tide-gauge.bin
	@particle flash --cloud tide-gauge-1 tide-gauge.bin

clean:
	rm -rf tide-gauge.bin
