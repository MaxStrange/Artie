# Update
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    i2c-tools \
    git \
    curl \
    vim \
    wget \
    python3 \
    python3-pip

python3 generate-requirements.py
pip3 install --user -r requirements.txt

# Make sure to enable various things in raspi-config
echo "Please enable i2c bus in raspi-config"
