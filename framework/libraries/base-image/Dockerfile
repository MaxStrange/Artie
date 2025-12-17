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

# Build artie-tooling lib
COPY ./tmp/artie-tooling /tmp/artie-tooling/
WORKDIR /tmp/artie-tooling
RUN pip install .
RUN rm -rf /tmp/artie-tooling

# Build artie-i2c lib
COPY ./tmp/artie-i2c /tmp/artie-i2c/
WORKDIR /tmp/artie-i2c
RUN pip install .
RUN rm -rf /tmp/artie-i2c

# Build artie-gpio lib
COPY ./tmp/artie-gpio /tmp/artie-gpio/
WORKDIR /tmp/artie-gpio
RUN pip install .[rpi]
RUN rm -rf /tmp/artie-gpio

# Build artie-service-client
COPY ./tmp/artie-service-client /tmp/artie-service-client/
WORKDIR /tmp/artie-service-client
RUN pip install .
RUN rm -rf /tmp/artie-service-client
