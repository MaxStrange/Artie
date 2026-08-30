ARG ARTIE_BASE_IMG=artie/ardk-base:latest
FROM ${ARTIE_BASE_IMG}

# Pip requirements. The ArDK entries are already satisfied by the base image, so pip
# treats them as no-ops; declaring them here keeps this driver's requirements explicit
# rather than implicit in whatever the base image happens to ship.
COPY ./requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r /tmp/requirements.txt

# Copy in the FW
ARG FW_FILE_NAME
ENV FW_PATH=/conf/mcu-fw.elf
COPY ./tmp/${FW_FILE_NAME} ${FW_PATH}

# Copy in the source
ARG DRIVER_TYPE
COPY ./src-${DRIVER_TYPE} /src

# Configuration stuff
ARG SERVER_PORT=18862
ENV PORT=${SERVER_PORT}
ENV ARTIE_RUN_MODE=production
ARG GIT_TAG=unversioned
ENV ARTIE_GIT_TAG=${GIT_TAG}
ENV ARTIE_LOG_LEVEL=INFO

# Default command is to run the application
WORKDIR /
CMD [ "/bin/bash", "-c", "python -m src.main ${FW_PATH} --port ${PORT}" ]
