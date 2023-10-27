from typing import List
from .. import common
from .. import kube
from . import artifact
from . import job
from . import result
import datetime
import enum

class DeploymentConfigurations(enum.StrEnum):
    """
    The possible deployment options. These should be chart names.
    """
    BASE = "artie-base"
    ARTIE_REFERENCE_STACK = "artie-reference"
    TELEOP = "artie-teleop"
    DEMO_STACK = "artie-demo"

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
        self.chart_reference = chart_reference

    def __call__(self, args) -> result.JobResult:
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
        if 'chart-version' in args:
            self.chart_version = args.chart_version
        if 'artie-name' in args:
            self.artie_name = args.artie_name
        super().fill_artifacts_at_runtime(args)

    def clean(self, args):
        # Nothing to do for temporary files and whatnot. If a user wants to delete the chart release, they need to run
        # the tool with the right command.
        pass
