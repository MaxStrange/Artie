# Compute Server Installation

Artie Compute Servers allow you to extend Artie's computational abilities, so that he can respond
faster or handle more complext work loads.

Artie Compute Server nodes are optional, so there are no real system requirements other than
the bare minimum requirements for the Artie stack itself, which mirror the [K3S requirements](https://docs.k3s.io/installation/requirements).

You will also need to make sure any compute servers you add are on the same local network
and don't have any firewall rules that block traffic on port 6443.

## Artie Computed

For each additional compute node you want to add, just follow these steps.

Once you have the Linux server up and running, download this git repository onto it and install the
comuted (or use the latest release, once we have releases):

* `sudo apt update`
* `sudo apt install -y git curl dos2unix`
* `git clone https://github.com/MaxStrange/Artie.git && cd Artie/artie-computed`
* `dos2unix ./install.sh && chmod +x ./install.sh`

At this point, you will need a few things:

* The token you got after installing Artie Admind. If you don't have it,
  you can find it by going to /var/lib/rancher/k3s/server/node-token on the admin server.
* The IP address of the admin server.

If you want to install Docker onto this machine as part of this installation, use this command:

```bash
sudo ./install.sh --token <the token from server> --host-ip <server ip address>
```

If you *do not want to install Docker* as part of this installation (because you already have
one working, perhaps because you are using a node that requires a special version of Docker, like
an NVIDIA Jetson device), use this command instead:

```bash
sudo ./install.sh --token <the token from server> --host-ip <server ip address> --no-docker
```
