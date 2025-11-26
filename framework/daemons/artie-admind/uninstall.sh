# !/bin/bash
set -eu

# Uninstall K3S
/usr/local/bin/k3s-uninstall.sh

# Install the daemon
sudo rm /etc/systemd/system/artie-admind.service
sudo systemctl daemon-reload
