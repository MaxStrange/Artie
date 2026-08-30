ARG ARTIE_BASE_IMG=thisarg/isrequired:latest
FROM ${ARTIE_BASE_IMG} AS BASE_IMG

RUN mkdir -p /pico/src/graphics/lcd

# The build context is this directory. Artie Tool stages the firmware source and the
# ArDK firmware libraries into ./tmp first (see the fw-mouth task's dependency-files),
# so this build does not need every component checked out under one shared root.
# The mouth firmware is built from the eyebrows source tree with its own CMakeLists.
COPY ./tmp/src /pico/src
COPY ./tmp/CMakeLists.txt /pico/src/CMakeLists.txt
COPY ./tmp/leds /pico/src/leds
COPY ./tmp/errors /pico/src/errors
COPY ./tmp/cmds /pico/src/cmds
WORKDIR /pico/src/build

ARG BUILD_TYPE=Debug
ARG LOG_LEVEL=INFO
RUN cmake -DCMAKE_BUILD_TYPE=${BUILD_TYPE} -DLOG_LEVEL=${LOG_LEVEL} .. && make -j4

CMD [ "/bin/bash", "-c", "echo 'build artifacts are located in /pico/src/build/' && sleep infinity" ]
