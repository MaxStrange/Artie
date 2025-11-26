FROM debian:bullseye

# Prereqs
RUN apt-get update && apt-get install -y \
    openssl \
    python3 \
    python3-pip \
    wget \
    dos2unix

# Pip
RUN pip3 install requests

# Install Prometheus
WORKDIR /app
RUN wget https://github.com/prometheus/prometheus/releases/download/v2.37.8/prometheus-2.37.8.linux-amd64.tar.gz -O prometheus.tar.gz
RUN tar -xzf prometheus.tar.gz -C . --strip-components=1 && rm prometheus.tar.gz

# Args for prometheus's shell script
ENV PORT=9090
ENV DATA_STORAGE_PATH=/data
ENV DATA_RETENTION_TIME=1y

# Prep some stuff for the launch script
RUN mkdir -p ${DATA_STORAGE_PATH}

# Copy in the config file
RUN mkdir -p /etc/prometheus
COPY ./prometheus.yaml /etc/prometheus/prometheus.yml

# Copy in the test config files
COPY ./test-configs/* /etc/prometheus/

# Copy in the launch script
COPY ./run.sh /run.sh
RUN chmod +x /run.sh && dos2unix /run.sh

# Copy the test script as well
COPY ./test.py /app/test.py

CMD [ "/run.sh" ]
