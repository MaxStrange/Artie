# Controller Node LED Driver

This is a simple user-space driver for controlling the LED
on the controller module PCB. It doesn't use a Docker container -
instead it should be installed directly into the Yocto image's
Systemd as a daemon.
