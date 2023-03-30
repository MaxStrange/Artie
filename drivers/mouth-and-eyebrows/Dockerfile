### FW Image
ARG FW_IMG
FROM ${FW_IMG} as FWBASEIMG

### Image to build OpenOCD (RPi variant)
FROM debian:bullseye as OPENOCDIMG

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    automake \
    autoconf \
    build-essential \
    texinfo \
    libtool \
    libftdi-dev \
    libusb-1.0-0-dev \
    pkg-config \
    git

WORKDIR /repos
RUN git clone https://github.com/raspberrypi/openocd.git --branch rp2040 --recursive --depth=1

WORKDIR /repos/openocd
RUN ./bootstrap && \
    ./configure --enable-ftdi --enable-sysfsgpio --enable-bcm2835gpio && \
    make -j4 && \
    make install

### The actual image
FROM python:3.11.2-bullseye

# Install dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    i2c-tools \
    libusb-0.1-4 \
    libusb-1.0-0 \
    libftdi1
RUN pip install \
    zerorpc \
    numpy \
    RPi.GPIO

# Build artie-i2c lib
COPY ./tmp/artie-i2c /tmp/artie-i2c/
WORKDIR /tmp/artie-i2c
RUN pip install .
RUN rm -rf /tmp/artie-i2c

# Build artie-util lib
COPY ./tmp/artie-util /tmp/artie-util/
WORKDIR /tmp/artie-util
RUN pip install .
RUN rm -rf /tmp/artie-util

# Copy in openocd
RUN mkdir -p /usr/local/share
RUN mkdir -p /usr/local/bin
COPY --from=OPENOCDIMG /usr/local/share/openocd /usr/local/share/openocd
COPY --from=OPENOCDIMG /usr/local/bin/openocd /usr/local/bin/

# Create the OpenOCD swd.cfg files from the board config
ENV SWD_CONFIG_MOUTH=raspberrypi-mouth-swd.cfg
ENV SWD_CONFIG_RIGHT=raspberrypi-right-swd.cfg
ENV SWD_CONFIG_LEFT=raspberrypi-swd.cfg
COPY ./conf/populate_swd_config.py /scripts/populate_swd_config.py
WORKDIR /scripts
RUN python populate_swd_config.py && \
    cp ./raspberrypi-right-swd.cfg /usr/local/share/openocd/scripts/interface/${SWD_CONFIG_RIGHT} && \
    cp ./raspberrypi-swd.cfg /usr/local/share/openocd/scripts/interface/${SWD_CONFIG_LEFT} && \
    cp ./raspberrypi-mouth-swd.cfg /usr/local/share/openocd/scripts/interface/${SWD_CONFIG_MOUTH} && \
    cd / && \
    rm -rf /scripts

# Copy in the FW
ENV FW_PATH=/conf/mcu-fw.elf
COPY --from=FWBASEIMG /pico/src/build/*.elf ${FW_PATH}

# Copy in the source
ARG DRIVER_TYPE
COPY ./src-${DRIVER_TYPE} /src

# Configuration stuff
ARG RPC_PORT=4242
ENV PORT=${RPC_PORT}
ENV LOGLEVEL=info

# Default command is to run the application
WORKDIR /src
CMD [ "/bin/bash", "-c", "python main.py ${FW_PATH} --port ${PORT} --loglevel ${LOGLEVEL}" ]