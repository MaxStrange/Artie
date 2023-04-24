# Base Image for Artie Docker components
FROM python:3.11.2-bullseye

# Install dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    i2c-tools \
    libusb-0.1-4 \
    libusb-1.0-0 \
    libftdi1 \
    openssl
RUN pip install \
    rpyc

# Build artie-util lib
COPY ./tmp/artie-util /tmp/artie-util/
WORKDIR /tmp/artie-util
RUN pip install .
RUN rm -rf /tmp/artie-util

# Build artie-i2c lib
COPY ./tmp/artie-i2c /tmp/artie-i2c/
WORKDIR /tmp/artie-i2c
RUN pip install .
RUN rm -rf /tmp/artie-i2c

# Build artie-gpio lib
COPY ./tmp/artie-gpio /tmp/artie-gpio/
WORKDIR /tmp/artie-gpio
RUN pip install .
RUN rm -rf /tmp/artie-gpio

# Build artie-swd
COPY ./tmp/artie-swd /tmp/artie-swd/
WORKDIR /tmp/artie-swd
RUN pip install .
RUN rm -rf /tmp/artie-swd

# Build artie-driver-client
COPY ./tmp/artie-driver-client /tmp/artie-driver-client/
WORKDIR /tmp/artie-driver-client
RUN pip install .
RUN rm -rf /tmp/artie-driver-client
