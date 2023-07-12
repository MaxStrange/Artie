# !/bin/bash
set -eu

Help()
{
   echo "Artie Admind Installation"
   echo
   echo "Syntax: install.sh [-h] [--help|--no-docker]"
   echo
   echo "Options:"
   echo "--no-docker     Do not install Docker. This is useful if you already have a Docker configuration set up."
   echo "-h | --help     Print this Help."
   echo
}

NO_DOCKER=0

optspec=":h-:"
while getopts "$optspec" optchar; do
   case "${optchar}" in
      -)
         case "${OPTARG}" in
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

# Install docker
if [[ "$NO_DOCKER" == 1 ]]; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
fi

# Install K3S
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.26.6+k3s1" INSTALL_K3S_EXEC="--write-kubeconfig-mode=644" sh -
sudo ufw allow 6443/tcp

# Update K3S to require Artie Admind
sudo sed -i '/After=network-online.target/a PartOf=artie-admind.service' /etc/systemd/system/k3s.service

# Install the daemon
sudo cp ./artie-admind.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart k3s.service
sudo systemctl start artie-admind.service
sudo systemctl enable artie-admind.service

# Print the Token for the user, as they will need it for the next few steps in installing Artie
TOKEN=$(sudo cat /var/lib/rancher/k3s/server/node-token)
MSG="The following token is important for the next few steps of Artie installation. If you lose this token, you can always find it at /var/lib/rancher/k3s/server/node-token on this machine."
echo $MSG
echo $TOKEN
