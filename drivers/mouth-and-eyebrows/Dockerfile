ARG OPENOCD_IMG
ARG ARTIE_BASE_IMG
FROM ${OPENOCD_IMG} AS OPENOCDIMG
FROM ${ARTIE_BASE_IMG}

# Pip requirements
RUN pip install numpy==1.24.3

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
ARG FW_FILE_NAME
ENV FW_PATH=/conf/mcu-fw.elf
COPY ./tmp/${FW_FILE_NAME} ${FW_PATH}

# Copy in the source
ARG DRIVER_TYPE
COPY ./src-${DRIVER_TYPE} /src

# Configuration stuff
ARG RPC_PORT=18862
ENV PORT=${RPC_PORT}
ENV LOGLEVEL=info
ENV ARTIE_RUN_MODE=production
ARG GIT_TAG=unversioned
ENV ARTIE_GIT_TAG=${GIT_TAG}

# Default command is to run the application
WORKDIR /
CMD [ "/bin/bash", "-c", "python -m src.main ${FW_PATH} --port ${PORT} --loglevel ${LOGLEVEL}" ]
