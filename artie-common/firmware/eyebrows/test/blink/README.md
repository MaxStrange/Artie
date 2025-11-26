# Eyebrows FW Test: Blink

This test blinks the Pico's onboard LED. It's just straight from the documentation.

## Building and Running

1. From this directory, run: `docker build -f Dockerfile -t artie-eyebrows-test-blink:$(git log --format="%h" -n 1) .`
1. Now start that image in one process and in another,
   copy out the binaries with `docker cp <pid>:/pico/pico-examples/build/blink/blink.elf ./`
   and `docker cp <pid>:/pico/pico-examples/build/blink/blink.uf2 ./`
1. Stop the process by looking it up `docker ps` then `docker stop <process ID>`
1. Plug the pico into the host computer *while holding down the onboard BOOTSEL button*. It should enumerate as a USB mass storage device.
1. Drag and drop the uf2 file into it.
1. Watch the LED blink on and off.