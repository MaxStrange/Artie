# docker build -f Dockerfile -t artie-eyebrows-test-i2c:$(git log --format="%h" -n 1) ..
ARG I2C=external

FROM ubuntu:latest AS base

RUN apt-get update && apt-get install -y \
    cmake \
    gcc-arm-none-eabi \
    libnewlib-arm-none-eabi \
    build-essential \
    git \
    libstdc++-arm-none-eabi-newlib \
    python3 \
    p7zip-full \
    wget \
    && \
    apt-get autoclean -y && apt-get autoremove -y

RUN mkdir -p /pico/i2c-test/build

WORKDIR /pico
RUN git clone --recurse-submodules https://github.com/raspberrypi/pico-sdk.git
RUN git clone https://github.com/raspberrypi/pico-examples.git
RUN git clone https://github.com/raspberrypi/pico-extras.git
RUN git clone https://github.com/raspberrypi/pico-playground.git
RUN git clone https://github.com/vmilea/pico_i2c_slave && \
    mv pico_i2c_slave/i2c_slave /pico/i2c-test/
RUN cp /pico/pico-sdk/external/pico_sdk_import.cmake /pico/i2c-test/pico_sdk_import.cmake

FROM base AS base-external
COPY ./src/main.c /pico/i2c-test/main.c

FROM base AS base-self
COPY ./src/self_test_main.c /pico/i2c-test/main.c

FROM base AS base-selfv2
COPY ./src/self_test_v2_main.c /pico/i2c-test/main.c

FROM base-${I2C}

ENV PICO_SDK_PATH=/pico/pico-sdk
WORKDIR /pico/i2c-test/build
COPY ./src/CMakeLists.txt /pico/i2c-test/CMakeLists.txt
RUN cmake .. && make -j4

CMD [ "/bin/bash", "-c", "sleep infinity" ]