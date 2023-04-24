ARG ARTIE_BASE_IMG
FROM ${ARTIE_BASE_IMG} AS BASE_IMG

COPY ./src /pico/src
WORKDIR /pico/src/build

ARG BUILD_TYPE=Debug
ARG LOG_LEVEL=INFO
RUN cmake -DCMAKE_BUILD_TYPE=${BUILD_TYPE} -DLOG_LEVEL=${LOG_LEVEL} .. && make -j4

CMD [ "/bin/bash", "-c", "echo 'build artifacts are located in /pico/src/build/' && sleep infinity" ]
