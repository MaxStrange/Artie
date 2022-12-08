# Command Line Interface

This folder contains a CLI for Artie. This program is meant to be used for debugging low-level testing of Artie
to ensure he is functioning properly. It isn't the main way you should be interacting with Artie.
[See other options for deployment of experiments](../README.md#deploying-experiments).

## Using the CLI

To use the CLI tool, ensure you have the latest version of Python installed, then install
the requirements with `pip install -r ./requirements` from this directory.

You may also need to install the FTDI driver for your host computer.

1. Plug a USB cable between your host computer and Artie's control module.
1. Run `python cli.py <port>` to connect to Artie's serial console.
1. Type `help` to get a display of the available commands and their arguments.
1. When done, simply unplug the cable.
