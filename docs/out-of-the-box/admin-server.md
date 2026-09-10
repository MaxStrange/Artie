# Admin Server Installation

The Artie Admin Server is the component of the system that does much of the behind-the-scenes infrastructure
work for an Artie cluster. This includes:

* Maintaining all the microservices
* Collecting telemetry
* Potentially storing data, including telemetry

TODO: Figure out minimum system requirements

## Artie Admind

Once you have the Linux server up and running, download the ArtieDaemons git repository onto it and install the
admind daemon (or use the latest release, once we have releases):

* `sudo apt update`
* `sudo apt install -y git curl dos2unix`
* `git clone https://github.com/ArtieBots/ArtieDaemons.git && cd ArtieDaemons/artie-admind`
* `dos2unix ./install.sh && chmod +x ./install.sh`
* `sudo ./install.sh`

Copy the token that is output at the end of the installation process and save it somewhere safe. You will need it later
when you add a robot to this Kubernetes cluster (which is what you just started by the way).

Verify that the admind service is running:

* `sudo systemctl status artie-admind`

This should show that the service is active and running. If not, check the logs with:

* `sudo journalctl -u artie-admind -f`

The admind service will automatically start on boot. This daemon ensures that K3S (the Kubernetes distribution we use)
is running on startup.
