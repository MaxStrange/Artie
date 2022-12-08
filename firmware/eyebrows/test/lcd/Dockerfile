# docker build -f Dockerfile -t artie-eyebrows-test-lcd:$(git log --format="%h" -n 1) ..
ARG SIZE="1.14"
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
RUN mkdir -p /pico/waveshare-lcd/c

WORKDIR /pico
RUN git clone --recurse-submodules https://github.com/raspberrypi/pico-sdk.git
RUN git clone https://github.com/raspberrypi/pico-examples.git
RUN git clone https://github.com/raspberrypi/pico-extras.git
RUN git clone https://github.com/raspberrypi/pico-playground.git
RUN wget https://www.waveshare.com/w/upload/2/28/Pico_code.7z && \
    7z x Pico_code.7z -o./waveshare-lcd
COPY ./src/main.c /pico/waveshare-lcd/c/main.c

FROM base AS base-1.14
RUN sed -i 's://LCD_2in_test():LCD_1in14_V2_test():g' /pico/waveshare-lcd/c/main.c

FROM base AS base-2
RUN sed -i 's://LCD_2in_test():LCD_2in_test():g' /pico/waveshare-lcd/c/main.c

FROM base-${SIZE}
ENV PICO_SDK_PATH=/pico/pico-sdk
WORKDIR /pico/waveshare-lcd/c/build
RUN cmake .. && make -j4
CMD [ "/bin/bash", "-c", "sleep infinity" ]