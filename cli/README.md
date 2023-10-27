# Command Line Interface

This folder contains a CLI for Artie. This program is meant to be used for debugging and low-level testing of Artie
to ensure he is functioning properly. It isn't the main way you should be interacting with Artie.
[See other options for deployment of experiments](../README.md).

## Installing

(For development)

On Ubuntu, you may have to use this command:

```bash
DEB_PYTHON_INSTALL_LAYOUT=deb_system pip install --user .[remote]
```

See [this issue](https://github.com/pypa/setuptools/issues/3269#issuecomment-1254507377) for explanation.

On other systems, you should be able to do this:

```bash
pip install --user .[remote]
```

## Using the CLI

Artie's Controller Module comes pre-installed with this CLI program.
To use it, plug a USB cable into the UART terminal of Artie's Controller Module enclosure,
then use whatever serial console you want to communicate. The program `artie-cli` should be
available in the Controller Module system's path. However, this CLI is built without the [remote]
dependencies, which means it can only interact with the hardware directly and cannot
access the cluster.

You can also use Artie CLI from your development machine, but it will require authentication
into the Kubernetes cluster.
