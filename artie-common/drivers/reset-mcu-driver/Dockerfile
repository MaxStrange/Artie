ARG ARTIE_BASE_IMG=thisarg/isrequired:latest
FROM ${ARTIE_BASE_IMG}

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
