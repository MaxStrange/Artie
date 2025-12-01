# Admin Server Installation

The Artie Admin Server is the component of the system that does much of the behind-the-scenes infrastructure
work for Artie. This includes:

* Maintaining all the microservices
* Collecting telemetry
* Potentially storing data, including telemetry
* Serving the Artie web application

TODO: Figure out minimum system requirements

## Artie Admind

Once you have the Linux server up and running, download this git repository onto it and install the
admind (or use the latest release, once we have releases):

* `sudo apt update`
* `sudo apt install -y git curl dos2unix`
* `git clone https://github.com/MaxStrange/Artie.git && cd Artie/framework/daemons/artie-admind`
* `dos2unix ./install.sh && chmod +x ./install.sh`
* `sudo ./install.sh`
