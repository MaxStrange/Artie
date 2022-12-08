# docker build -f Dockerfile -t artie-eyebrows-test-blink:$(git log --format="%h" -n 1) .
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

WORKDIR /pico
RUN git clone --recurse-submodules https://github.com/raspberrypi/pico-sdk.git
RUN git clone https://github.com/raspberrypi/pico-examples.git
RUN git clone https://github.com/raspberrypi/pico-extras.git
RUN git clone https://github.com/raspberrypi/pico-playground.git

ENV PICO_SDK_PATH=/pico/pico-sdk

WORKDIR /pico/pico-examples/build
RUN cmake .. && cd blink && make -j4

# We've now built blink.elf and blink.uf2 in /pico/pico-examples/build/blink

CMD [ "/bin/bash", "-c", "sleep infinity" ]
