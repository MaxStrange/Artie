# Build context is one folder up (..)
ARG ARTIE_BASE_IMG=thisarg/isrequired:latest
FROM ${ARTIE_BASE_IMG}

# Create working directory
RUN mkdir -p /cli
WORKDIR /cli

# Copy in CLI
COPY . ./

# Build and install CLI
RUN pip install .[remote]

# Copy in Artie's profiles
COPY ./test/integration_test_profile.json /integration_test_profile.json
COPY ./test/unit_test_profile.json /unit_test_profile.json

# Default command is to run help and exit
CMD [ "/bin/bash", "-c", "artie-cli help" ]
