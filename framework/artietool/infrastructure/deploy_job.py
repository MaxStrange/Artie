from typing import List
from .. import common
from .. import workspace
from .. import kube
from . import artifact
from . import job
from . import result
import datetime
import enum

def _release_image_tags(args) -> dict:
    """
    The per-image tags implied by the release manifest in force, if there is one.

    Reads the manifest's `images` section, which already records which version each image
    was built with, rather than re-deriving it from the component versions here.
    """
    release_file = getattr(args, 'release_file', None)
    if not release_file:
        return {}

    try:
        manifest = workspace.load_release_manifest(release_file)
    except ValueError as e:
        common.error(f"Could not apply release manifest: {e}")
        return {}

    return manifest.get('images') or {}


class DeploymentConfigurations(enum.StrEnum):
    """
    The possible deployment options. These should be chart names.
    """
    BASE = "artie-base"
    ARTIE_REFERENCE_STACK = "artie-reference"
    TELEOP = "artie-teleop"
    DEMO_STACK = "artie-demo"
    CUSTOM = "artie-custom"

class AddDeployJob(job.Job):
    """
    An AddDeployJob deploys a set of items to Artie's runtime.
    """
    def __init__(self, artifacts: List[artifact.Artifact], what: DeploymentConfigurations, chart_reference: str) -> None:
        super().__init__(artifacts)
        self.what = what
        self.chart_name = what
        self.chart_version = None  # Comes from args, otherwise we use whatever is in the Chart.yaml
        self.artie_name = None  # Comes from args, otherwise we determine from the cluster
        self.deployment_repo = None  # Comes from args, otherwise we use whatever is in the Values.yaml
        self.chart_reference = chart_reference

    def __call__(self, args) -> result.JobResult:
        # First decide what the name of the rlease is
        if hasattr(args, 'release_name') and args.release_name is not None:
            common.info(f"Using release name from args: {args.release_name}")
            self.what = common.replace_vars_in_string(args.release_name, args)
            self.chart_name = common.replace_vars_in_string(args.release_name, args)

        # Check if we are overriding the chart path
        if hasattr(args, 'chart_path') and args.chart_path is not None:
            common.info(f"Using chart path from args: {args.chart_path}")
            self.chart_reference = common.replace_vars_in_string(args.chart_path, args)

        # Now either deploy or remove the chart
        if args.delete:
            return self._remove_helm_chart(args)
        else:
            return self._deploy_helm_chart(args)

    def _remove_helm_chart(self, args):
        common.info(f"Removing deployment: {self.what}...")

        kube.uninstall_helm_chart(args, self.chart_name)
        success = not kube.check_if_helm_chart_is_deployed(args, self.chart_name)
        if not success:
            raise RuntimeError("Could not uninstall the Helm chart for some reason.")

        self.mark_all_artifacts_as_built()
        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def _deploy_helm_chart(self, args):
        common.info(f"Deploying {self.what}...")
        common.info(f"Checking for previous failed deployments...")
        status = kube.check_helm_chart_status(args, self.chart_name)
        if status and status != kube.HelmChartStatuses.DEPLOYED:
            common.info(f"Found previous non-successful release. Deleting...")
            kube.delete_helm_release(args, self.chart_name)

        common.info(f"Deploying chart...")
        sets = {}
        if self.chart_version:
            sets['appVersion'] = self.chart_version
            sets['imageTag'] = self.chart_version

        # Under a release manifest the images do not share a tag: each carries the version
        # of the component that produced it. Pass them through per image, keyed by image
        # name, which is exactly how the charts look them up.
        for image_name, version in _release_image_tags(args).items():
            sets[f'imageTags.{image_name}'] = version

        if self.deployment_repo:
            sets['repository'] = self.deployment_repo

        if self.artie_name:
            sets['artieId'] = self.artie_name
        else:
            names_of_arties_on_cluster = kube.get_artie_names(args)
            if len(names_of_arties_on_cluster) == 1:
                self.artie_name = names_of_arties_on_cluster[0]
                sets['artieId'] = self.artie_name
            elif len(names_of_arties_on_cluster) > 1:
                raise ValueError(f"More than one Artie detected on cluster: {names_of_arties_on_cluster} ; Please pass --artie-name flag to select one.")
            elif len(names_of_arties_on_cluster) == 0:
                raise ValueError(f"Could not detect any Arties on the cluster. Cannot proceed with deployment.")

        kube.install_helm_chart(args, self.chart_name, self.chart_reference, sets)

        timeout_s = 60 * 5
        common.info(f"Verifying deployment of {self.what}. This will timeout after {timeout_s/60:.2f} minutes if we don't succeed by then...")
        start = datetime.datetime.now().timestamp()
        success = False
        while datetime.datetime.now().timestamp() - start <= timeout_s and not success:
            success = kube.check_if_helm_chart_is_deployed(args, self.chart_name)

        if not success:
            raise RuntimeError("Helm chart was deployed, but we can't find it after deployment for some reason.")

        self.mark_all_artifacts_as_built()
        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def fill_artifacts_at_runtime(self, args):
        if 'chart_version' in args:
            self.chart_version = args.chart_version
        if 'artie_name' in args:
            self.artie_name = args.artie_name
        if 'deployment_repo' in args:
            self.deployment_repo = args.deployment_repo
        super().fill_artifacts_at_runtime(args)

    def clean(self, args):
        # Nothing to do for temporary files and whatnot. If a user wants to delete the chart release, they need to run
        # the tool with the right command.
        pass
