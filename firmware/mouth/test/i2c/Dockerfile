# docker build -f Dockerfile -t artie-mouth-uart-test:$(git log --format="%h" -n 1) .
FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    cmake \
    gcc-arm-none-eabi \
    libnewlib-arm-none-eabi \
    build-essential \
    git \
    libstdc++-arm-none-eabi-newlib \
    python3 \
    wget \
    && \
    apt-get autoclean -y && apt-get autoremove -y
RUN mkdir -p /pico/src/graphics/lcd

WORKDIR /pico
ARG PICO_RELEASE=1.5.0
RUN git clone --depth 1 --branch ${PICO_RELEASE} --recurse-submodules https://github.com/raspberrypi/pico-sdk.git
RUN git clone --depth 1 --branch sdk-${PICO_RELEASE} https://github.com/raspberrypi/pico-examples.git
RUN git clone --depth 1 --branch sdk-${PICO_RELEASE} https://github.com/raspberrypi/pico-extras.git
RUN git clone --depth 1 --branch sdk-${PICO_RELEASE} https://github.com/raspberrypi/pico-playground.git
RUN git clone https://github.com/vmilea/pico_i2c_slave && \
    mv pico_i2c_slave/i2c_slave /pico/src/
RUN cp /pico/pico-sdk/external/pico_sdk_import.cmake /pico/src/pico_sdk_import.cmake

ENV PICO_SDK_PATH=/pico/pico-sdk

COPY ./src /pico/src
WORKDIR /pico/src/build

ARG BUILD_TYPE=Debug
ARG LOG_LEVEL=INFO
RUN cmake -DCMAKE_BUILD_TYPE=${BUILD_TYPE} -DLOG_LEVEL=${LOG_LEVEL} .. && make -j4

CMD [ "/bin/bash", "-c", "echo 'build artifacts are located in /pico/src/build/' && sleep infinity" ]
