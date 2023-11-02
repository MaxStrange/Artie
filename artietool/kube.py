"""
Wrapper around the Kubernetes API for convenience stuff.
"""
from typing import Dict
from typing import List
from typing import Tuple
from . import common
import dataclasses
import enum
import json
import kubernetes as k8s
import subprocess

class ArtieK8sKeys(enum.StrEnum):
    """
    An enum of available Artie labels/annotations, etc.
    """
    ARTIE_ID = "artie/artie-id"
    NODE_ROLE = "artie/node-role"
    PHYSICAL_BOT_NODE_TAINT = "artie/physical-bot-node"
    CONTROLLER_NODE_TAINT = "artie/controller-node"

class ArtieK8sValues(enum.StrEnum):
    """
    An enum of known values for labels/annotations, etc.
    """
    CONTROLLER_NODE_ID = "controller-node"
    NAMESPACE = "artie"

class HelmChartStatuses(enum.StrEnum):
    """
    Possible status values for a Helm Chart.
    """
    UNKNOWN = "unknown"
    DEPLOYED = "deployed"
    UNINSTALLED = "uninstalled"
    SUPERSEDED = "superseded"
    FAILED = "failed"
    UNINSTALLING = "uninstalling"
    PENDING_INSTALL = "pending-install"
    PENDING_UPGRADE = "pending-upgrade"
    PENDING_ROLLBACK = "pending-rollback"

class TaintEffects(enum.StrEnum):
    """
    Possible effects of node taints.
    """
    NO_SCHEDULE = "NoSchedule"  # Kubernetes will not schedule the pod onto that node
    PREFER_NO_SCHEDULE = "PreferNoSchedule"  # Kubernetes will try to not schedule the pod onto the node
    NO_EXECUTE = "NoExecute"  # The pod will be evicted from the node (if it is already running on the node), and will not be scheduled onto the node (if it is not yet running on the node).

@dataclasses.dataclass
class HelmChart:
    """
    A Helm chart class to keep track of its various bits.
    """
    # The name of the Helm chart, as used in deployments.
    name: str
    # The version to use for this Helm chart or None, in which case we do not override the chart's value for this.
    version: str | None
    # The chart reference, typically a path to one on the file system, but could be a URL.
    chart: str

def _configure(args):
    """
    Load the Kube config from the environment.
    """
    config_file = args.kube_config
    k8s.config.load_kube_config(config_file=config_file)

def _get_node_from_name(v1: k8s.client.CoreV1Api, name: str):
    """
    Retrieve the API node object that has the given name in the cluster.
    Raises ValueError if we can't find the node.
    """
    node_list = v1.list_node().items
    for node in node_list:
        if node.metadata.name == name:
            return node

    raise ValueError(f"Cannot find node {name} in cluster.")

def _handle_transient_network_errors(cmd: List[str], n=5):
    """
    Run the given `cmd` up to `n` times, returning (whether we succeeded or not, retcode, stderr, stdout).
    """
    n_retries = 3
    i = 1
    p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    while i < n_retries and p.returncode !=0 and 'tcp' in p.stdout.lower() or 'tcp' in p.stderr.lower():
        common.warning(f"Networking error. Retrying.")
        p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
        i += 1
    return p.returncode == 0, p.returncode, p.stderr, p.stdout

def add_helm_repo(name: str, url: str):
    """
    Add a Helm repo.
    """
    subprocess.run(["helm", "repo", "add", name, url]).check_returncode()

def assign_node_labels(args, node_name: str, labels: Dict[str, str]):
    """
    Assigns the given labels to the the given node.
    Labels should be a dict of labels to values.
    """
    body = {
        "metadata": {
            "labels": labels
        }
    }
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    node = _get_node_from_name(v1, node_name)
    v1.patch_node(node.metadata.name, body)

def assign_node_taints(args, node_name: str, node_taints: Dict[str, Tuple[str, TaintEffects]]):
    """
    Assign the given node taints to the given node. `node_taints` should be a
    dict of the form:
    {
        taint_key: (taint_value, taint_effect)
    }
    """
    body = {
        "spec": {
            "taints": [
                {
                    "effect": effect,
                    "key": key,
                    "value": val,
                } for key, (val, effect) in node_taints.items()
            ]
        }
    }
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    node = _get_node_from_name(v1, node_name)
    v1.patch_node(node.metadata.name, body)

def check_if_helm_chart_is_deployed(args, chart_name: str, namespace=ArtieK8sValues.NAMESPACE) -> bool:
    """
    Checks if the given chart name is present in the cluster.

    Convenience function for check_helm_chart_status() == HelmChartStatuses.deployed
    """
    return check_helm_chart_status(args, chart_name, namespace) == HelmChartStatuses.DEPLOYED

def check_helm_chart_status(args, chart_name: str, namespace=ArtieK8sValues.NAMESPACE) -> HelmChartStatuses|None:
    """
    Returns the status for the given chart, or None if it isn't found in the namespace.
    """
    cmd = ["helm", "list", "--kubeconfig", args.kube_config, "--namespace", namespace, "--filter", chart_name, "--output", "json"]
    success, retcode, stderr, stdout = _handle_transient_network_errors(cmd)
    if not success:
        raise OSError(f"Helm failed: {stderr}; {stdout}")

    json_object = json.loads(stdout)
    if len(json_object) == 0:
        return None
    elif len(json_object) > 1:
        # Regex matched more than one chart name for some reason. This probably shouldn't
        # have happened. Just look for the first exact match and return that one.
        for o in json_object:
            if o['name'] == chart_name:
                return HelmChartStatuses(o['status'])
        raise AssertionError("This shouldn't be possible: regex matched more than one chart name, but then couldn't find the chart with the right name.")
    else:
        return HelmChartStatuses(json_object[0]['status'])

def delete_node(args, node_name: str, ignore_errors=False):
    """
    Remove the given node from the cluster as gracefully as we can.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    try:
        v1.delete_node(node_name, propagation_policy='Foreground')  # delete dependant children, then parents
    except Exception as e:
        if not ignore_errors:
            raise e

def get_artie_names(args) -> List[str]:
    """
    Returns a list of names of Arties found on the cluster.
    """
    ret = []
    node_names = get_node_names(args)
    for node_name in node_names:
        if node_name.startswith("controller-node-"):
            ret.append(node_name.removeprefix("controller-node-"))
    return ret

def get_node_names(args) -> List[str]:
    """
    Returns a list of node names - one for each one found in the cluster.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    node_list = v1.list_node()
    names = [node.metadata.name for node in node_list.items]
    return names

def get_node_labels(args, node_name: str) -> Dict[str, str]:
    """
    Gets the dict of node label key:value pairs for the given node.
    Raises a ValueError if the node is not found in the cluster.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    node = _get_node_from_name(v1, node_name)
    return node.metadata.labels

def install_helm_chart(args, name: str, chart: str, sets=None, namespace=ArtieK8sValues.NAMESPACE):
    """
    Install the given Helm chart, overriding any keys given in the `sets` dict with the corresponding values.
    """
    if sets is None:
        sets = {}

    # Base command
    cmd = ["helm", "install", "--kubeconfig", args.kube_config, "--namespace", namespace, "--create-namespace", "--wait", "--timeout", str(args.kube_timeout_s) + 's']

    # Add value overrides
    for k, v in sets.items():
        cmd += ["--set", f"{k}={v}"]

    # Command suffix
    cmd += [name, chart]

    # Run the command
    success, retcode, stderr, stdout = _handle_transient_network_errors(cmd)
    if not success:
        common.error(f"Helm chart installation failed.")
        try:
            if not check_if_helm_chart_is_deployed(args, name, namespace):
                common.error(f"Attempting to clean up after ourselves...")
                delete_helm_release(args, name, namespace)
        except Exception as e:
            cleancmd = f"helm delete --kubeconfig {args.kube_config} --namespace {namespace} --wait {name}"
            common.warning(f"Could not clean up the failed Helm deployment. You may need to do so manually with {cleancmd}. Error deploying in the first place: {stderr}; {stdout}")
            raise e
        raise OSError(f"Helm failed: {stderr}; {stdout}")

def delete_helm_release(args, chart_name: str, namespace=ArtieK8sValues.NAMESPACE):
    """
    Delete the given Helm chart.
    """
    status = check_helm_chart_status(args, chart_name, namespace)
    if not status:
        common.info(f"Helm release {chart_name} not present. Cannot delete it.")
        return

    cmd = ["helm", "delete", "--kubeconfig", args.kube_config, "--namespace", namespace, "--wait", chart_name, "--timeout", str(args.kube_timeout_s) + 's']
    success, retcode, stderr, stdout = _handle_transient_network_errors(cmd)
    if not success:
        raise OSError(f"Helm failed: {stderr}; {stdout}")

def node_is_online(args, node_name: str) -> bool:
    """
    Returns True if the we can see the given node is online. False otherwise.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    node_list = v1.list_node().items
    for node in node_list:
        if node.metadata.name == node_name:
            conditions = node.status.conditions
            for c in conditions:
                if c.type == "Ready" and c.status != "True":
                    return False
                elif c.type == "Ready" and c.status == "True":
                    return True
    # Couldn't find the node
    return False

def uninstall_helm_chart(args, name: str, namespace=ArtieK8sValues.NAMESPACE):
    """
    Uninstall the given chart.
    """
    cmd = ["helm", "uninstall", "--namespace", namespace, "--wait", name, "--timeout", str(args.kube_timeout_s) + 's']
    success, retcode, stderr, stdout = _handle_transient_network_errors(cmd)
    if not success:
        raise OSError(f"Error uninstalling chart: {stderr}; {stdout}")

def verify_access(args) -> Tuple[bool, Exception|None]:
    """
    Check that we have access to the cluster. Returns True if we do, False if we don't.
    If we fail to connect, we also return the exception.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    try:
        v1.list_node()
        return True, None
    except Exception as e:
        return False, e
