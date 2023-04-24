#! /bin/bash
# Generate the certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 36500 -nodes -keyout /pkey.pem -out /cert.pem -subj /C=US/ST=Washington/L=Seattle/O=Artie/OU=Artie/CN=metrics-collector

# Put the certs where the yaml file expects them
mkdir -p /etc/prometheus/
mv /cert.pem /etc/prometheus/cert.pem
mv /pkey.pem /etc/prometheus/pkey.pem

# Run Prometheus metrics collector
if [[ $TEST_ENV ]]; then
    echo "Using test configuration"
    /app/prometheus --web.listen-address="0.0.0.0:${PORT}" \
                    --storage.tsdb.path="${DATA_STORAGE_PATH}" \
                    --storage.tsdb.retention.time=${DATA_RETENTION_TIME} \
                    --config.file=/etc/prometheus/metrics-integration-tests.yaml \
                    &

    sleep 6
    echo "Running test..."
    python3 /app/test.py
    retval=$?
    if [[ $retval -ne 0 ]]; then
        echo "Test Failed"
    else
        echo "Test Passed"
    fi
    while [[ true ]]; do true; sleep 5; done
else
    echo "Using production configuration"
    /app/prometheus --web.listen-address="0.0.0.0:${PORT}" \
                    --storage.tsdb.path="${DATA_STORAGE_PATH}" \
                    --storage.tsdb.retention.time=${DATA_RETENTION_TIME}
fi
