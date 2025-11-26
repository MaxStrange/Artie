ARG ARTIE_BASE_IMG
FROM ${ARTIE_BASE_IMG}

# Pip requirements
RUN pip install flask==2.3

# Copy in the files
COPY ./src /app

# Install apt dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    dos2unix
RUN chmod +x /app/run.sh && dos2unix /app/run.sh

# Configuration stuff
ARG SERVE_ON_PORT=8782
ENV PORT=${SERVE_ON_PORT}
ENV LOGLEVEL=info
ENV ARTIE_RUN_MODE=production
ARG GIT_TAG=unversioned
ENV ARTIE_GIT_TAG=${GIT_TAG}

# Default command is to run the application
WORKDIR /app
CMD [ "./run.sh" ]
