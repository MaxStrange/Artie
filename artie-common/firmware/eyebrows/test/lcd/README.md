# Eyebrows FW Test: LCD

This test performs some basic operations on the Waveshare LCD screen, making use of
the Waveshare LCD's example program.

## Building and Running

1. Plug the LCD shield into the Pico.
1. From this directory, run: `docker build -f Dockerfile --build-arg SIZE=<SIZE> -t artie-eyebrows-test-lcd:$(git log --format="%h" -n 1) .`
   where `<SIZE>` is either `"1.14"` or `"2"` (for the different sized LCDs).
1. Now start that image in one process and in another,
   copy out the binaries with `docker cp <pid>:/pico/waveshare-lcd/c/build/main.elf ./`
   and `docker cp <pid>:/pico/waveshare-lcd/c/build/main.uf2 ./`
1. Plug the pico into the host computer *while holding down the onboard BOOTSEL button*. It should enumerate as a USB mass storage device.
1. Drag and drop the uf2 file into it.