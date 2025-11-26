#! /bin/bash
# Check for --help arg
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    python main.py --help
    flask --app main run --help
    exit 0
fi

# Generate the certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 36500 -nodes -keyout /pkey.pem -out /cert.pem -subj /C=US/ST=Washington/L=Seattle/O=CompanyName/OU=Org/CN=www.example.com

# Put the certs somewhere
mkdir -p /etc/certs
cp /cert.pem /etc/certs/cert.pem
cp /pkey.pem /etc/certs/pkey.pem

# Run flask
flask --app main run --host=0.0.0.0 --port=${PORT} --cert="/etc/certs/cert.pem" --key="/etc/certs/pkey.pem"
