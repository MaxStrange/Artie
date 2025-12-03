ARG ARTIE_BASE_IMG
FROM ${ARTIE_BASE_IMG}

# Pip requirements
RUN pip install numpy==1.24.3

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
