# Eyebrows FW Test: UART

This test blinks the Pico's UART.

## Building and Running

1. From this directory, run: `docker build -f Dockerfile --build-arg USE_USB=1 -t artie-eyebrows-test-uart:$(git log --format="%h" -n 1) .`
1. Now start that image in one process and in another,
   copy out the binaries with `docker cp <pid>:/pico/pico-examples/build/hello_world/usb/hello_usb.elf ./`
   and `docker cp <pid>:/pico/pico-examples/build/hello_world/usb/hello_usb.uf2 ./`
1. Plug the pico into the host computer *while holding down the onboard BOOTSEL button*. It should enumerate as a USB mass storage device.
1. Drag and drop the uf2 file into it.
1. Unplug the pico, then plug in again *without* holding down BOOTSEL. You should now be able to connect
   to it over your preferred terminal application at baudrate 115200.

Note: To build so that you use the UART pins instead of the USB port,
get the firmware from `/pico/pico-examples/build/hello_world/serial/hello_serial.[elf/uf2]`.
If you do this, you will need an FTDI chip for converting from USB to UART, and you'll want the Pico's RX pin on
the Pico's pin 2. Pico's TX is Pico pin 1. *OR* if you want to use a Raspberry Pi as host, you can simply hook
up the Pi's UART pins to the Pico's UART pins: Pi Pin 10 to Pico Pin 1; Pi Pin 8 to Pico Pin 2. Make sure
to enable the UART in raspi-config first and ensure to connect grounds together.