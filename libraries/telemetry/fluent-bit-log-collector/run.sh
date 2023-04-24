#! /bin/bash
# Generate the certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 36500 -nodes -keyout /pkey.pem -out /cert.pem -subj /C=US/ST=Washington/L=Seattle/O=CompanyName/OU=Org/CN=www.example.com

# Put the certs where the conf file expects them
mkdir -p /etc/fluent-bit
cp ./cert.pem /etc/fluent-bit/cert.pem
cp ./pkey.pem /etc/fluent-bit/pkey.pem

# Run fluent bit log collector
/opt/fluent-bit/bin/fluent-bit -c /etc/fluent-bit/config.conf
