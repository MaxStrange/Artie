"""
Semi-permeable wrapper around the Kubernetes API for convenience stuff.
"""
from typing import Dict
from typing import List
from typing import Tuple
from . import common
from artie_tooling import hw_config
import argparse
import io
import dataclasses
import enum
import io
import json
import kubernetes as k8s
import subprocess
import urllib3
import yaml

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

class JobStatuses(enum.StrEnum):
    """
    Possible statuses for a Kubernetes Job.
    """
    INCOMPLETE = "Incomplete"  # At least one pod is not done running
    FAILED = "Failed"  # At least one pod has 'failed' status
    SUCCEEDED = "Succeeded"  # All pods have completed and succeeded
    UNKNOWN = "Unknown"  # Can't determine the state of this job

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

def _configure(args: argparse.Namespace, need_artie_name: bool = False):
    """
    Load the Kube config from the environment. If `need_artie_name` is `True`, we
    also configure `args` with 'artie_name` based on the only Artie we find in the cluster.
    If no 'artie_name' is given, `need_artie_name` is `True`, and there is more than one or less
    than one Artie on the cluster, we raise a ValueError (for zero Arties) or a KeyError (for more than one Artie).
    """
    config_file = args.kube_config
    k8s.config.load_kube_config(config_file=config_file)

    if need_artie_name:
        _determine_artie_name(args)

def _determine_artie_name(args: argparse.Namespace) -> argparse.Namespace:
    """
    Determine what Artie name we want to use. If the user has not specified one and we can't
    determine it from the cluster, we throw an exception.

    This function adds the appropriate argument ('artie_name') to `args`
    if `args` does not already have it, and it fills in the value if the value
    is not already filled in by the user.
    """
    if 'artie_name' in args and args.artie_name is not None:
        return args

    args.artie_name = None
    names = get_artie_names(args)
    if len(names) == 0:
        raise ValueError(f"Cannot find any deployed Arties.")
    elif len(names) > 1:
        raise KeyError(f"Cannot determine a unique Artie ID from the cluster. More than one found. Please specify a single one with --artie-name. Names found: {names}")
    else:
        args.artie_name = names[0]
        return args

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

def delete_pod(args, pod_name: str, namespace=ArtieK8sValues.NAMESPACE, ignore_errors=False):
    """
    Delete a K8s Pod.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(pod_name, namespace, grace_period_seconds=0, propagation_policy='Foreground')
    except Exception as e:
        if not ignore_errors:
            raise e
        else:
            common.warning(f"Error deleting pod {namespace}:{pod_name}: {e}")

def delete_configmap(args, name: str, namespace=ArtieK8sValues.NAMESPACE, ignore_errors=False):
    """
    Delete a configmap.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    try:
        v1.delete_namespaced_config_map(name, namespace, grace_period_seconds=0, propagation_policy='Foreground')
    except Exception as e:
        if not ignore_errors:
            raise e
        else:
            common.warning(f"Error deleting config map {namespace}:{name}: {e}")

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
        else:
            common.warning(f"Error deleting node {node_name}: {e}")

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

def get_artie_hw_config(args) -> hw_config.HWConfig:
    """
    Access the Artie cluster to retrieve the hardware configuration for an Artie.

    After this call, we guarantee `args` has `artie_name` in it.
    """
    _configure(args, need_artie_name=True)
    v1 = k8s.client.CoreV1Api()
    
    # Retrieve the ConfigMap
    configmap_name = f'artie-hw-config-{args.artie_name}'
    try:
        configmap = v1.read_namespaced_config_map(configmap_name, ArtieK8sValues.NAMESPACE)
    except k8s.client.exceptions.ApiException as e:
        if e.status == 404:
            raise ValueError(f"Hardware configuration ConfigMap '{configmap_name}' not found for Artie '{args.artie_name}'. Artie must be installed through Workbench or Artie Tool.")
        else:
            raise

    buf = io.BytesIO(configmap.data.encode())
    conf = hw_config.HWConfig.from_config(buf)
    return conf

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

def _update_helm_dependencies(args, chart: str):
    """
    Update Helm chart dependencies if the chart has any.
    Silently succeeds if there are no dependencies or if the chart doesn't exist.
    """
    import pathlib
    
    # Check if chart path is a directory
    chart_path = pathlib.Path(chart)
    if not chart_path.is_dir():
        return
    
    # Check if Chart.yaml exists and has dependencies
    chart_yaml = chart_path / "Chart.yaml"
    if not chart_yaml.exists():
        return
    
    # Read Chart.yaml to check for dependencies
    try:
        import yaml
        with open(chart_yaml, 'r') as f:
            chart_data = yaml.safe_load(f)
        
        if not chart_data or 'dependencies' not in chart_data:
            return
        
        # Chart has dependencies, update them
        common.info(f"Updating Helm chart dependencies for {chart_path.name}...")
        cmd = ["helm", "dependency", "update", str(chart_path)]
        
        success, retcode, stderr, stdout = _handle_transient_network_errors(cmd)
        if not success:
            common.warning(f"Failed to update chart dependencies: {stderr}")
        else:
            common.info(f"Successfully updated dependencies for {chart_path.name}")
    
    except Exception as e:
        common.warning(f"Could not check/update chart dependencies: {e}")

def install_helm_chart(args, name: str, chart: str, sets=None, namespace=ArtieK8sValues.NAMESPACE):
    """
    Install the given Helm chart, overriding any keys given in the `sets` dict with the corresponding values.
    """
    if sets is None:
        sets = {}

    # Update chart dependencies if the chart has any
    _update_helm_dependencies(args, chart)

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

def check_job_status(args, job_name: str, namespace=ArtieK8sValues.NAMESPACE) -> JobStatuses:
    """
    Check and return the status of the given job.
    """
    _configure(args)
    v1 = k8s.client.BatchV1Api()

    try:
        job = v1.read_namespaced_job_status(job_name, namespace)
        status = job.status

        if status.active is not None and status.active > 0:
            # At least one pod is still pending or running
            return JobStatuses.INCOMPLETE
        elif status.failed is not None and status.failed > 0:
            # At least one pod failed
            return JobStatuses.FAILED
        elif status.succeeded is not None and status.succeeded > 0:
            # No active or failed pods AND at least one pod is successful. Looks good.
            return JobStatuses.SUCCEEDED
        else:
            # Can't understand this state. No active, failed, or succeeded pods.
            common.error(f"Kubernetes job {namespace}:{job_name} has unknown status - no active, failed, or succeeded pods.")
            return JobStatuses.UNKNOWN
    except urllib3.exceptions.MaxRetryError:
        common.warning(f"Could not get the status for k8s job {namespace}:{job_name}; transient networking error")
        return JobStatuses.UNKNOWN

def get_pods_from_job(args, job_name: str, namespace=ArtieK8sValues.NAMESPACE) -> List[k8s.client.V1Pod]:
    """
    Get all the pods for a given job and return them as a List of K8s Job objects.
    """
    _configure(args)
    v1 = k8s.client.BatchV1Api()

    #job = v1.read_namespaced_job(job_name, namespace)

    v1 = k8s.client.CoreV1Api()
    podlist = v1.list_namespaced_pod(namespace, label_selector=f"job-name={job_name}")
    return podlist.items

def get_all_pods(args, namespace=ArtieK8sValues.NAMESPACE) -> List[k8s.client.V1Pod]:
    """
    Get all pods for the given namespace.
    """
    _configure(args)
    v1 = k8s.client.CoreV1Api()
    podlist = v1.list_namespaced_pod(namespace)
    return podlist.items

def log_job_results(args, job_name: str, namespace=ArtieK8sValues.NAMESPACE):
    """
    Log all lines from all pods in the given job.
    """
    pods = get_pods_from_job(args, job_name, namespace)
    _configure(args)
    v1 = k8s.client.CoreV1Api()

    for pod in pods:
        logs = v1.read_namespaced_pod_log(pod.metadata.name, namespace)
        common.info(f"Reading logs from pod {namespace}:{pod.metadata.name}:")
        for line in logs.splitlines():
            common.info(line.rstrip())

def delete_job(args, job_name: str, namespace=ArtieK8sValues.NAMESPACE, ignore_errors=False):
    """
    Delete a K8s job.
    """
    _configure(args)
    v1 = k8s.client.BatchV1Api()
    try:
        v1.delete_namespaced_job(job_name, namespace, grace_period_seconds=0, propagation_policy='Foreground')
    except Exception as e:
        if not ignore_errors:
            raise e
        else:
            common.warning(f"Error deleting job {namespace}:{job_name}: {e}")

def create_from_yaml(args, yaml_contents: str, namespace=ArtieK8sValues.NAMESPACE):
    """
    Create a K8s resource from the given `yaml_contents`, which should be a YAML definition
    like you would put in the K8s YAMl file.

    Returns the list of items that were created from the YAML file, or the single object
    that was created in the case that the list would only contain one object.
    """
    _configure(args)
    client = k8s.client.ApiClient()

    # Convert from raw YAML into Python
    yaml_object = yaml.safe_load(io.StringIO(yaml_contents))
    result = k8s.utils.create_from_yaml(client, yaml_objects=[yaml_object], namespace=namespace)

    # For whatever reason, the create_from_yaml function creates randomly nested lists.
    while hasattr(result, '__len__') and len(result) == 1 and not issubclass(type(result), dict):
        result = result[0]

    return result

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
