ARG OPENOCD_IMG
ARG ARTIE_BASE_IMG
FROM ${OPENOCD_IMG} AS OPENOCDIMG
FROM ${ARTIE_BASE_IMG}

# Copy in openocd
RUN mkdir -p /usr/local/share
RUN mkdir -p /usr/local/bin
COPY --from=OPENOCDIMG /usr/local/share/openocd /usr/local/share/openocd
COPY --from=OPENOCDIMG /usr/local/bin/openocd /usr/local/bin/

# Create the OpenOCD swd.cfg file from the board config
ENV SWD_CONFIG_RESET=raspberrypi-reset-swd.cfg
COPY ./conf/populate_swd_config.py /scripts/populate_swd_config.py
WORKDIR /scripts
RUN python populate_swd_config.py && \
    cp ./raspberrypi-reset-swd.cfg /usr/local/share/openocd/scripts/interface/${SWD_CONFIG_RESET} && \
    cd / && \
    rm -rf /scripts

# Copy in the FW
ARG FW_FILE_NAME=reset-mcu.elf
ENV FW_PATH=/conf/mcu-fw.elf
COPY ./tmp/${FW_FILE_NAME} ${FW_PATH}

# Copy in the source
COPY ./src /src

# Configuration stuff
ARG RPC_PORT=4242
ENV PORT=${RPC_PORT}
ENV LOGLEVEL=info
ENV ARTIE_RUN_MODE=production
ARG GIT_TAG=unversioned
ENV ARTIE_GIT_TAG=${GIT_TAG}

# Default command is to run the application
WORKDIR /src
CMD [ "/bin/bash", "-c", "python main.py ${FW_PATH} --port ${PORT} --loglevel ${LOGLEVEL}" ]
