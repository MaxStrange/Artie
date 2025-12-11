# !/bin/bash
set -eu

# Uninstall K3S
/usr/local/bin/k3s-uninstall.sh

# Uninstall the daemon
sudo rm /etc/systemd/system/artie-admind.service
sudo rm -f /etc/sysctl.d/90-kubelect.conf
sudo systemctl daemon-reload
