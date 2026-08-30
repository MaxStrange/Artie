ARG ARTIE_BASE_IMG=artie/ardk-base:latest
FROM ${ARTIE_BASE_IMG}

# Pip requirements. The ArDK entries are already satisfied by the base image, so pip
# treats them as no-ops; declaring them here keeps this service's requirements explicit
# rather than implicit in whatever the base image happens to ship.
COPY ./requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r /tmp/requirements.txt

# Copy in the source
COPY ./src /src

# Configuration stuff
ARG SERVICE_PORT=18865
ENV PORT=${SERVICE_PORT}
ENV ARTIE_RUN_MODE=production
ARG GIT_TAG=unversioned
ENV ARTIE_GIT_TAG=${GIT_TAG}
ENV ARTIE_LOG_LEVEL=INFO

# Default command is to run the application
WORKDIR /
CMD [ "/bin/bash", "-c", "python -m src.main --port ${PORT}" ]
