# Build context is one folder up (..)
FROM python:3.11.2-bullseye

RUN mkdir -p /cli
WORKDIR /cli

# Copy in CLI
COPY . ./

# Build and install CLI
RUN pip install .

# Default command is to run help and exit
CMD [ "/bin/bash", "-c", "artie-cli help" ]
