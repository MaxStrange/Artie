"""
All the machinery for uninstalling.
"""
from .. import common
from .. import kube
from typing import List
import argparse
import datetime
import getpass
import time

def _all_nodes_removed(args, node_names: List[str]) -> bool:
    """
    Return True if all expected nodes have been removed from the cluster.
    """
    for node in node_names:
        if kube.node_is_online(args, node):
            return False
    return True

def _wait_for_node_removal(args, node_names: List[str]) -> bool:
    """
    Block until we timeout or finish removing all the nodes.

    Returns True if we succeed. False if we time out.
    """
    ts = datetime.datetime.now().timestamp()
    timeout_s = 30
    while not _all_nodes_removed(args, node_names):
        time.sleep(1)
        if datetime.datetime.now().timestamp() - ts > timeout_s:
            common.error("Timed out waiting for node removal.")
            return False
    return True

def uninstall(args):
    """
    Top-level uninstall function.
    """
    retcode = 0

    # Check that args makes sense
    if not args.cluster_only:
        if not args.artie_ip:
            common.error(f"Need the IP address of the Artie we are uninstalling. Please pass either --cluster-only or --artie-ip <IP>")
            retcode = 1
            return retcode
        if not args.username:
            common.error(f"Need the username for the Artie we are uninstalling. Please pass either --cluster-only or --username <USERNAME>")
            retcode = 1
            return retcode

    # Check that we have kubectl access
    common.info("Checking for access to the cluster...")
    access, err = kube.verify_access(args)
    if not access:
        common.error(f"Could not access the Artie cluster: {err}")
        retcode = 1
        return retcode

    # Check for any already installed arties and get their names
    common.info("Checking existing Arties...")
    node_names_to_remove = []
    node_names = kube.get_node_names(args)
    for node in node_names:
        labels = kube.get_node_labels(args, node)
        if kube.ArtieK8sKeys.ARTIE_ID in labels and labels[kube.ArtieK8sKeys.ARTIE_ID] == args.artie_name:
            node_names_to_remove.append(node)

    if not node_names_to_remove and args.cluster_only:
        common.warning(f"Could not find {args.artie_name} in the cluster. Nothing to do.")
        retcode = 0
        return retcode

    # Ask for password if we don't have it
    if not args.cluster_only:
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

    # Remove Artie from the cluster
    for node in node_names_to_remove:
        common.info(f"Removing {node}...")
        kube.delete_node(args, node)

    # Wait until Artie is removed from cluster, or timeout waiting
    common.info(f"Waiting for Artie with ID {args.artie_name} to be removed from the cluster...")
    removed = _wait_for_node_removal(args, node_names_to_remove)
    if not removed:
        retcode = 1
        return retcode

    # If that's all, we can exit now
    if args.cluster_only:
        return retcode

    # Remove the cluster's configuration file from Artie so he can't join the cluster again.
    # Restart Artie's k3s agent
    common.info("Disabling Artie from joining the cluster...")
    common.ssh("rm /etc/rancher/k3s/config.yaml", artie_ip, artie_username, artie_password, fail_okay=True)
    common.ssh("systemctl daemon-reload", artie_ip, artie_username, artie_password, fail_okay=True)
    common.ssh("systemctl restart k3s-agent.service", artie_ip, artie_username, artie_password, fail_okay=True)

    # Delete the ghost node now that it has nothing attached to it, ignoring any exceptions.
    for node in node_names_to_remove:
        kube.delete_node(args, node, ignore_errors=True)

    return retcode

def fill_subparser(parser_uninstall: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    parser_uninstall.add_argument("--cluster-only", action='store_true', help="If given, we only remove the given Artie from the cluster, but do not attempt to disable Artie from rejoining the cluster if his power is cycled.")
    parser_uninstall.add_argument("-u", "--username", default=None, type=str, help="Username for the Artie we are uninstalling. Required unless --cluster-only.")
    parser_uninstall.add_argument("--artie-ip", default=None, type=common.validate_input_ip, help="IP address for the Artie we are uninstalling. Required unless --cluster-only.")
    parser_uninstall.add_argument("-p", "--password", type=str, default=None, help="The password for the Artie we are removing. It is more secure to pass this in over stdin when prompted, if possible.")
    parser_uninstall.set_defaults(cmd=uninstall, module="uninstall-artie")
