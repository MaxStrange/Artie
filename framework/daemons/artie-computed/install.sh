# !/bin/bash
set -eu

Help()
{
   echo "Artie Computed Installation"
   echo
   echo "Syntax: install.sh [-h] [--help|--host-ip|--token|--no-docker]"
   echo "Arguments:"
   echo "--host-ip       Required. The IP address of the Artie Admind machine."
   echo "--token         Required. The token that you were given after installing the Artie Admin daemon. Can also be found on that machine at /var/lib/rancher/k3s/server/node-token"
   echo
   echo "Options:"
   echo "--no-docker     Do not install Docker. This is useful if you already have a Docker configuration set up."
   echo "-h | --help     Print this Help."
   echo
}

NO_DOCKER=0
URL=""
TOKEN=""

optspec=":h-:"
while getopts "$optspec" optchar; do
   case "${optchar}" in
      -)
         case "${OPTARG}" in
            host-ip)
               val="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ))
               URL="https://$val:6443"
               ;;
            host-ip=*)
               val=${OPTARG#*=}
               URL="https://$val:6443"
               ;;
            token)
               val="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ))
               TOKEN="$val"
               ;;
            token=*)
               val=${OPTARG#*=}
               TOKEN="$val"
               ;;
            no-docker)
               NO_DOCKER=1
               ;;
            help)
               Help
               exit 2
               ;;
            *)
               if [ "$OPTERR" = 1 ] && [ "${optspec:0:1}" != ":" ]; then
                  echo "Unknown option --${OPTARG}" >&2
               fi
               ;;
         esac;;
         h)
            Help
            exit 2
            ;;
         *)
            if [ "$OPTERR" != 1 ] || [ "${optspec:0:1}" = ":" ]; then
               echo "Non-option argument: '-${OPTARG}'" >&2
            fi
            ;;
   esac
done

if [[ -z "$TOKEN" ]]; then
   echo "Missing --token argument."
   exit 1
fi

if [[ -z "$URL" ]]; then
   echo "Missing --host-ip argument"
   exit 1
fi

# Install docker
if [[ "$NO_DOCKER" != 1 ]]; then
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
fi

# Install K3S (version is limited by Yocto compatibility. See: https://layers.openembedded.org/layerindex/branch/master/layer/meta-virtualization/)
# By passing K3S_URL, we set this node to be a K3S agent, as opposed to a server.
# INSTALL_K3S_NAME tells the installer what to call the systemd service file.
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.32.0+k3s1" K3S_URL=$URL INSTALL_K3S_NAME="k3s-agent" K3S_TOKEN=$TOKEN INSTALL_K3S_EXEC="--write-kubeconfig-mode=644" sh -s - --docker

# Pin Docker to the current version to avoid unwanted automatic upgrades
sudo apt-mark hold docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-ce-rootless-extras docker-buildx-plugin docker-model-plugin

# Open the firewall for the K3S API server
sudo ufw allow 6443/tcp

# Update K3S to require Artie Computed
sudo sed -i '/After=network-online.target/a PartOf=artie-computed.service' /etc/systemd/system/k3s-agent.service

# Install the daemon
sudo cp ./artie-computed.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart k3s-agent.service
sudo systemctl start artie-computed.service
sudo systemctl enable artie-computed.service
