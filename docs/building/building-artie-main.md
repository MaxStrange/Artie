# Building Artie

This guide shows you how to build a physical Artie robot from scratch.

## Prerequisites

You will need the following items:

* A development computer - the computer can be running any OS that supports git, Docker, and Helm/Kubectl.
* A 3D printer - as many of the parts as possible are 3D-printable using a small-volume, budget 3D printer
* Electrical and mechanical components - some parts can't be fabricated on your own; in particular motors, sensors,
  microcontrollers, single board computers, etc. You can find a list of all the required components in the
  bill of materials document for the Artie you are building. If you are building Artie00,
  [that can be found here](https://github.com/ArtieBots/Artie00/blob/main/bom.md).
* Soldering equipment - you are going to have to get your hands dirty to put the circuit boards together.

### Setting up your Development Computer

Ensure that your development computer has the following software installed. **Carefully note the version requirements.**

- Python 3.14+
- [Kubectl](https://kubernetes.io/docs/tasks/tools/) - v1.32
- [Helm](https://helm.sh/docs/intro/quickstart/) - 4.0 (don't install Kubernetes separately - we install K3S for you
  as part of setting up the Artie system later on)
- If you haven't already, make sure to install the Python dependencies for Artie Tool after cloning this repo:
  `pip install -r requirements.txt` from the 'framework' directory of the repo.
  **See the [Note on Python Installation](#note-on-python-installation)**
  if you are running Linux.

**NOTE** On your development machine, in addition to Docker, you will also need
to deal with Qemu:

* If you are on Ubuntu: `sudo apt install qemu-user-static`
* If you are on Windows: `docker run --privileged --rm tonistiigi/binfmt --install all` then `docker run --rm --privileged multiarch/qemu-user-static --reset -p yes -c yes` (you may have to do this every time you boot up Docker Desktop or whatever).

### Note on Python Installation

If you are running Windows, it is easy to install whatever version of Python you want
and then pip install various requirements.

If you are running Linux on the other hand, Python has been absorbed into the system package manager
and trying to actually use it for development can be quite a headache. Feel free to use virtual environments,
though I personally don't use them, so your mileage may vary.

If you are running Linux, I personally do the following:

1. Download a release of Python's **source**: https://www.python.org/downloads/source/
1. Unzip it wherever and change directories into it.
1. Install dependencies: https://devguide.python.org/getting-started/setup-building/index.html#install-dependencies
   Don't forget the optional dependencies.
1. `./configure --enable-optimizations --with-lto=full --with-pydebug`
1. `make -s -j$(nproc)`
1. `make altinstall` **This is critical** - do NOT just do the normal 'make install'
1. Now install packages by means of the alternate installed pip: `python3.14 -m pip install foo` (for example).

### Install Artie Workbench on Your Development Machine

Run `pip install artieworkbench`, or clone https://github.com/ArtieBots/ArtieWorkbench and run `pip install .` in it.
You should now be able to run Artie Workbench from anywhere by running `artie-workbench`.
(TODO: Artie Workbench is not published to PyPI yet, so for now clone the repository and
install from it.)

## Get the circuit boards

To procure the circuit boards:

1. Find and buy all the electrical components you need from the BOM.
1. TODO: Figure out where we will release gerber files for a particular Artie. Do we keep them in the repo?
   Or do we just keep them in releases on GitHub? Probably the latter. The KiCad project files should be
   put somewhere too. This repo?
1. Send the gerber files to a fab place like [OSH Park](https://oshpark.com/) which can make the circuit boards cheaply.

While you are waiting for the circuit boards to arrive, you can start 3D printing the parts you need.

## 3D Print Stuff

Fire up your 3D printer and print all the items found in the BOM that are 3D-printable. Make sure you are using the right
settings and filament type (PLA, PETG, ABS, etc.), as specified in the BOM.

## Assembly

TODO
