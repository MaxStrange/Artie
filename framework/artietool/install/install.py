"""
All the machinery for installing.
"""
from typing import Dict
from typing import List
from typing import Tuple
from .. import common
from ..infrastructure import hw_config
from .. import kube
import argparse
import datetime
import getpass
import os
import re
import subprocess
import time
import yaml

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

def _initialize_sbc(args, sbc_config: hw_config.SBC, artie_name: str, artie_ip: str, artie_username: str, 
                    artie_password: str, k3s_token: str, admin_ip: str) -> Tuple[bool, str]:
    """
    Initialize a single board computer by creating its K3S config and joining it to the cluster.
    
    Returns: (success, node_name)
    """
    node_name = f"{sbc_config.name}-{artie_name}"

    common.info(f"Initializing SBC: {sbc_config.name} (node: {node_name})...")

    # Create K3S config file
    config_file_contents = "\n".join([
        f'node-name: "{node_name}"',
        f'token: "{k3s_token}"',
        f'server: "https://{admin_ip}:6443"',
    ])
    
    config_file = os.path.join(common.get_scratch_location(), f"config-{sbc_config.name}.yaml")
    with open(config_file, 'w') as f:
        f.write(config_file_contents)
    
    # Copy config to the SBC
    common.scp_to(artie_ip, artie_username, artie_password, target=config_file, dest="/etc/rancher/k3s/config.yaml")
    os.remove(config_file)
    
    # Restart k3s agent
    common.ssh("systemctl daemon-reload", artie_ip, artie_username, artie_password)
    common.ssh("systemctl restart k3s-agent.service", artie_ip, artie_username, artie_password)
    
    return True, node_name

def _create_artie_metadata_configmap(args, artie_name: str, artie_config: hw_config.HWConfig):
    """
    Create a ConfigMap in Kubernetes containing metadata about this Artie's hardware configuration.
    """
    common.info("Creating Artie hardware metadata ConfigMap...")
    
    # Build the metadata structure
    metadata = {
        'artie-name': artie_name,
        'single-board-computers': yaml.dump(artie_config.sbcs),
        'microcontrollers': yaml.dump(artie_config.mcus),
        'sensors': yaml.dump(artie_config.sensors),
        'actuators': yaml.dump(artie_config.actuators),
    }
    
    # Create ConfigMap YAML
    configmap_yaml = {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',
        'metadata': {
            'name': f'artie-hw-config-{artie_name}',
            'namespace': kube.ArtieK8sValues.NAMESPACE,
            'labels': {
                'app.kubernetes.io/name': 'artie-hw-config',
                'app.kubernetes.io/part-of': 'artie',
                kube.ArtieK8sKeys.ARTIE_ID: artie_name,
            }
        },
        'data': metadata
    }
    
    # Delete existing ConfigMap if it exists
    try:
        kube.delete_configmap(args, f'artie-hw-config-{artie_name}', ignore_errors=True)
    except:
        pass
    
    # Create the ConfigMap
    configmap_yaml_str = yaml.dump(configmap_yaml)
    kube.create_from_yaml(args, configmap_yaml_str)
    common.info(f"Created hardware metadata ConfigMap: artie-hw-config-{artie_name}")

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

    # Load Artie type configuration
    common.info(f"Loading Artie type configuration from {args.artie_type_file}...")
    try:
        artie_config = hw_config.HWConfig.from_config(args.artie_type_file)
        common.info(f"Found {len(artie_config.sbcs)} SBC(s), {len(artie_config.mcus)} MCU(s), {len(artie_config.sensors)} sensor(s), and {len(artie_config.actuators)} actuator(s).")
    except Exception as e:
        common.error(f"Failed to load Artie type configuration: {e}")
        retcode = 1
        return retcode

    # Assert that there is at least a controller node
    if artie_config.controller_node is None:
        common.error(f"No controller-node found in this Artie configuration. Cannot proceed with installation.")
        retcode = 1
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

    # Initialize all SBCs from the configuration file
    common.info(f"Initializing {len(artie_config.sbcs)} single board computer(s)...")
    initialized_nodes = []
    
    for sbc_config in artie_config.sbcs:
        # Initialize this SBC
        # TODO: When multiple SBCs have different IPs, update _initialize_sbc to handle that.
        #       The controller node will send the information along over CAN
        success, node_name = _initialize_sbc(args, sbc_config, artie_name, artie_ip, artie_username, artie_password, k3s_token, args.admin_ip)
        if not success:
            common.error(f"Failed to initialize SBC: {sbc_config.name}")
            retcode = 1
            return retcode
        
        # Wait for node to come online
        common.info(f"Waiting for {node_name} to come online...")
        timeout_s = 120
        start_time = datetime.datetime.now().timestamp()
        while not kube.node_is_online(args, node_name):
            time.sleep(1)
            if datetime.datetime.now().timestamp() - start_time > timeout_s:
                common.error(f"Timed out waiting for {node_name} to come online.")
                retcode = 1
                return retcode
        
        common.info(f"Node {node_name} is online.")
        initialized_nodes.append((node_name, sbc_config))
    
    # Assign labels and taints to all nodes
    common.info("Configuring node labels and taints...")
    for node_name, sbc_config in initialized_nodes:
        # Assign node labels
        node_labels = {
            kube.ArtieK8sKeys.ARTIE_ID: artie_name,
            kube.ArtieK8sKeys.NODE_ROLE: sbc_config.name,  # Use the SBC name as the node role
        }
        kube.assign_node_labels(args, node_name, node_labels)
        
        # Assign node taints - all physical bot nodes get the physical bot taint
        node_taints = {
            kube.ArtieK8sKeys.PHYSICAL_BOT_NODE_TAINT: ("true", "NoSchedule"),
        }
        
        # Controller node gets an additional taint
        if sbc_config.name == "controller-node":
            node_taints[kube.ArtieK8sKeys.CONTROLLER_NODE_TAINT] = ("true", "NoSchedule")
        
        kube.assign_node_taints(args, node_name, node_taints)
        common.info(f"Configured {node_name}")
    
    # Create ConfigMap with hardware metadata
    _create_artie_metadata_configmap(args, artie_name, artie_config)

    return retcode

def fill_subparser(parser_install: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    parser_install.add_argument("-u", "--username", required=True, type=str, help="Username for the Artie we are installing.")
    parser_install.add_argument("--artie-ip", required=True, type=common.validate_input_ip, help="IP address for the Artie we are installing.")
    parser_install.add_argument("--admin-ip", required=True, type=common.validate_input_ip, help="IP address for the admin server.")
    parser_install.add_argument("--artie-type-file", required=True, type=common.argparse_file_path_type, help="Path to the YAML file defining this Artie's hardware configuration (e.g., artie00/artie00.yml).")
    parser_install.add_argument("-p", "--password", type=str, default=None, help="The password for the Artie we are adding. It is more secure to pass this in over stdin when prompted, if possible.")
    parser_install.add_argument("-t", "--token", type=str, default=None, help="Token that you were given after installing Artie Admind. If you have lost it, you can find it on the admin server at /var/lib/rancher/k3s/server/node-token. It is more secure to pass this in over stdin when prompted, if possible.")
    parser_install.add_argument("--token-file", type=common.argparse_file_path_type, default=None, help="A file that contains the Artie Admind token as its only contents.")
    parser_install.set_defaults(cmd=install, module="install-artie")
