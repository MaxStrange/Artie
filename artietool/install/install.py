"""
All the machinery for installing.
"""
from typing import List
from typing import Tuple
from .. import common
from .. import kube
import argparse
import datetime
import getpass
import os
import re
import subprocess
import time

def _create_unique_artie_name(node_names: List[str]) -> str:
    """
    Create a name for Artie that is not already included in `artie_names`.
    """
    template_names = [n for n in node_names if re.compile("Artie-[0-9]+").match(n)]
    number_suffixes = [int(n.split('-')[1]) for n in template_names]
    if number_suffixes:
        highest_number = sorted(number_suffixes)[-1]
        return f"Artie-{highest_number+1:03d}"
    else:
        return f"Artie-{1:03d}"

def _validate_k3s_token(k3s_token: str) -> bool:
    """
    Return False if the given token is obviously invalid, otherwise return True.
    """
    if not k3s_token:
        return False
    elif "^V" in k3s_token:
        return False
    else:
        return True

def _get_token_from_file(args) -> Tuple[bool, str|None]:
    with open(args.token_file, 'r') as f:
        k3s_token = "".join([line.strip() for line in f.readlines()])

    if not _validate_k3s_token(k3s_token):
        common.error(f"The given token file {args.token_file} does not contain a valid token, or perhaps it contains more than just a token.")
        return False, None

    return True, k3s_token

def _get_token_from_user(args) -> Tuple[bool, str|None]:
    k3s_token = args.token if args.token is not None else getpass.getpass("Token: ").strip()
    valid_token = _validate_k3s_token(k3s_token)
    if not valid_token and args.token:
        common.error("Invalid token given via command line.")
        return False, None
    elif not valid_token and not args.token:
        while not _validate_k3s_token(k3s_token):
            common.error("Invalid token. If you are copying and pasting, this may be a bug in your shell or in Python's getpass. Try passing the token in via a file instead.")
            k3s_token = getpass.getpass("Token: ").strip()

    return True, k3s_token

def _get_token(args) -> Tuple[bool, str|None]:
    """
    Get the K3S token (somehow - based on args).
    """
    if args.token_file:
        return _get_token_from_file(args)
    else:
        return _get_token_from_user(args)

def install(args):
    """
    Top-level install function.
    """
    retcode = 0
    # Check that we have kubectl access
    common.info("Checking for access to the cluster...")
    access, err = kube.verify_access(args)
    if not access:
        common.error(f"Could not access the Artie cluster: {err}")
        retcode = 1
        return retcode

    # Check that we have helm installed
    common.info("Checking for Helm...")
    p = subprocess.run("helm version".split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if p.returncode != 0:
        common.error(f"Could not run helm command. Is Helm installed?")
        retcode = p.returncode
        return retcode

    # Check for any already installed arties and get their names
    common.info("Checking existing Arties...")
    node_names = kube.get_node_names(args)
    artie_name = args.artie_name if args.artie_name is not None else _create_unique_artie_name(node_names)
    common.info(f"Will use {artie_name} for this Artie's name.")

    # Ask for password if we don't have it
    artie_ip = args.artie_ip
    artie_username = args.username
    artie_password = args.password if args.password is not None else getpass.getpass("Artie's Password: ")

    # Check that we can access Artie
    common.info("Verifying that we can connect to Artie...")
    access, err = common.verify_ssh_connection(artie_ip, artie_username, artie_password)
    if not access:
        common.error(f"Cannot access Artie at IP address {artie_ip} with username {artie_username} and the given password: {err}")
        retcode = 1
        return retcode

    # Ask for token if we don't have it
    got_token, k3s_token = _get_token(args)
    if not got_token:
        common.error("Problem getting Artie token. Cannot proceed.")
        retcode = 1
        return retcode

    # TODO: When we add additional SBCs to Artie, this initialization scheme will need to change;
    #       I.e., we need a way of propagating this information onto all the SBCs (ideally using
    #       the same mechanism we use for propagating the wifi credentials to all the other SBCs - presumably
    #       some low-level daemon in the Yocto image that listens to the CAN bus.)
    # Create a config file and copy it over to /etc/rancher/k3s/config.yaml on Artie at args.username@args.artie_ip
    #   node-name: Artie's name
    #   token: token value
    #   server: admin node's URL
    common.info("Creating a configuration file for Artie...")
    node_name = f"controller-node-{artie_name}"
    config_file_contents = "\n".join([
        f'node-name: "{node_name}"',
        f'token: "{k3s_token}"',
        f'server: "https://{args.admin_ip}:6443"',
    ])
    config_file = os.path.join(common.get_scratch_location(), "config.yaml")
    with open(config_file, 'w') as f:
        f.write(config_file_contents)
    common.scp_to(artie_ip, artie_username, artie_password, target=config_file, dest="/etc/rancher/k3s/config.yaml")
    os.remove(config_file)

    # Restart Artie's k3s agent
    common.info("Joining Artie to the cluster...")
    common.ssh("systemctl daemon-reload", artie_ip, artie_username, artie_password)
    common.ssh("systemctl restart k3s-agent.service", artie_ip, artie_username, artie_password)

    # Give it a moment to let the node come online in the Kubernetes cluster
    common.info("Waiting a moment for node to come online...")
    timeout_s = 120
    now = datetime.datetime.now().timestamp()
    while not kube.node_is_online(args, node_name):
        time.sleep(1)
        if datetime.datetime.now().timestamp() - now > timeout_s:
            common.error("Timed out waiting for the controller node to come online.")
            retcode = 1
            return retcode

    # Assign whatever labels to the various nodes
    # TODO: Need to assign these to ALL physical Artie nodes (SBCs) - not just controller node
    node_labels = {
        kube.ArtieK8sKeys.NODE_ROLE: str(kube.ArtieK8sValues.CONTROLLER_NODE_ID),
        kube.ArtieK8sKeys.ARTIE_ID: artie_name,
    }
    common.info("Configuring nodes (step 1)...")
    kube.assign_node_labels(args, node_name, node_labels)

    # Assign node taints
    # TODO: Need to assign these to ALL physical Artie nodes (SBCs) - not just controller node
    node_taints = {
        kube.ArtieK8sKeys.PHYSICAL_BOT_NODE_TAINT: ("true", "NoSchedule"),
        kube.ArtieK8sKeys.CONTROLLER_NODE_TAINT: ("true", "NoSchedule"),
    }
    common.info("Configuring nodes (step 2)...")
    kube.assign_node_taints(args, node_name, node_taints)

    return retcode

def fill_subparser(parser_install: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    parser_install.add_argument("-u", "--username", required=True, type=str, help="Username for the Artie we are installing.")
    parser_install.add_argument("--artie-ip", required=True, type=common.validate_input_ip, help="IP address for the Artie we are installing.")
    parser_install.add_argument("--admin-ip", required=True, type=common.validate_input_ip, help="IP address for the admin server.")
    parser_install.add_argument("-p", "--password", type=str, default=None, help="The password for the Artie we are adding. It is more secure to pass this in over stdin when prompted, if possible.")
    parser_install.add_argument("-t", "--token", type=str, default=None, help="Token that you were given after installing Artie Admind. If you have lost it, you can find it on the admin server at /var/lib/rancher/k3s/server/node-token. It is more secure to pass this in over stdin when prompted, if possible.")
    parser_install.add_argument("--token-file", type=common.argparse_file_path_type, default=None, help="A file that contains the Artie Admind token as its only contents.")
    parser_install.add_argument("--artie-name", type=str, default=None, help="The name for this Artie. Must be unique among all the Arties in this cluster. If not given, we generate a unique one for you.")
    parser_install.set_defaults(cmd=install, module="install-artie")
