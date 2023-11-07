"""
Hold onto your butts, this is a wild ride.

The YAML test definition specifies one or more Artie CLI commands to run
and the submodule status values to expect as a result of the commands.

Normally, every hardware test suite would represent a single task, which could be run in the main
infrastructure as any other test task. But because hardware tests run as Kubernetes jobs,
there's a lot of transient nonsense and overhead involved in running them. Because of this,
I really want to only run a single Kubernetes hardware test job, regardless of the tests that were selected
to run.

TODO: This paragraph isn't true yet. Right now we have it set up to turn each YAML file into a single test job. We should have all YAMLs selected turned into a single test job.
So, we scoop up all the hardware tests selected by the user and import them, combining them all into
a single HardwareTestJob that has a single test step - but this step is composed of all the
tests.

The HardwareTestJob has a setup step that creates the Kubernetes job definition, which includes
a job and a config map. The job runs a script which is mapped into the job's container by the config map.
The job's container is just the normal Artie CLI container, so we need to use the config map to get
the test script (which specifies how to run the CLI and interpret its outputs) into the container - that's why we use the config map.

The test script is composed dynamically - it first creates a python script that can interpret outputs from the CLI,
then it adds each test to the shell script. The result is something that looks like this:

artie-cli eyebrows status --artie-id artie-001 | python interpret_test_output.py
artie-cli mouth status --artie-id artie-001 | python interpret_test_output.py
artie-cli reset status --artie-id artie-001 | python interpret_test_output.py
etc.

The script is written such that it should fail and return an exit code if any of its commands
return non-zero exit codes. If the script fails, the Kubernetes job fails, and the result
is reported by means of the standard infrastructure. If none of the script steps fail,
the job passes.

The job is created and run by the CollectedHardwareTestSteps object when the step is called
by the infrastructure, its timeout is handled, and its results are checked by the normal __call__ method.
"""
from typing import List
from ..infrastructure import result
from ..infrastructure import test_job
from .. import common
from .. import docker
from .. import kube

class CollectedHardwareTestSteps:
    """
    The logic that we run inside the single hardware test job.
    """
    def __init__(self, steps: List[test_job.HWTest]) -> None:
        self.steps = steps
        self.job_def = None  # Filled in during test setup

    def __call__(self, args) -> result.TestResult:
        # Launch the k8s job
        res = self._launch_k8s_job(args)

        # TODO: This is example code
        ##################################################################################################
        # Launch the CLI command
        res = self._run_cli(args)
        if res.status != result.TestStatuses.SUCCESS:
            return res

        # Check the DUT(s) output(s)
        results = self._check_duts(args)
        results = [r for r in results if r is not None and r.status != result.TestStatuses.SUCCESS]

        # If we got more than one result, let's log the various problems and just return the first failing one
        if len(results) > 1:
            common.error(f"Multiple failures detected in {self.test_name}. Returning the first detected failure and logging all of them.")

        for r in results:
            common.error(f"Error in test {self.test_name}: {r.to_verbose_str()}")

        if results:
            return results[0]

        return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=result.TestStatuses.SUCCESS)
        ##################################################################################################

    def _determine_artie_id(self, args) -> str:
        """
        Determine what Artie ID we want to use. If the user has not specified one and we can't
        determine it from the cluster, we throw an exception.
        """
        if 'artie_name' in args and args.artie_name is not None:
            return args.artie_name

        names = kube.get_artie_names(args)
        if len(names) == 0:
            raise ValueError(f"Cannot find any deployed Arties. Cannot run HW Tests.")
        elif len(names) > 1:
            raise ValueError(f"Cannot determine a unique Artie ID from the cluster. More than one found. Please specify a single one with --artie-name. Names found: {names}")
        else:
            return names[0]

    def _determine_version(self, args) -> str:
        """
        Returns the version we should annotate the job def with.
        """
        if 'docker_tag' in args and args.docker_tag is not None:
            return args.docker_tag
        else:
            return common.git_tag()

    def _determine_docker_registry(self, args) -> str:
        """
        Returns the docker registry we should use to pull the CLI image.
        If the user has not specified one, we attempt to pull from Docker Hub and throw
        an exception if we can't find it there.
        """
        if 'docker_repo' in args and args.docker_repo is not None:
            return args.docker_repo

        default = "maxfieldstrange"
        image = f"{default}/artie-cli:{self._determine_version(args)}"
        common.info(f"Double checking that the CLI image can be accessed from default Dockerhub location...")
        success = docker.check_and_pull_if_docker_image_exists(args, image)
        if not success:
            raise ValueError(f"Cannot pull CLI image {image} ; Please specify a --docker-repo and --docker-tag that exist.")
        else:
            return default

    def _convert_test_into_script(self, args, artie_id: str, test_def: test_job.HWTest) -> str:
        """
        Returns a single test's contents as lines in a script.

        A test will usually have the following style of output:

        ```
        (artie-id) module:
            submodule01: [working, degraded, not working, or unknown]
            submodule02: [working, degraded, not working, or unknown]
            etc.
        ```
        """
        # E.g. artie-cli eyebrows status --artie-id artie-001
        cmd = test_def.cmd_to_run_in_cli + f" --artie-id {artie_id}"

        # We run the command and pipe it into a python script we create dynamically here
        contents = f"""
echo '{}' > interpret_test_output.py
{cmd} | python interpret_test_output.py\n
"""

        # TODO: Figure out from test def how we validate the output

        return contents

    def _determine_test_script_contents(self, artie_id: str, args) -> str:
        """
        Returns the contents of the script the CLI image job will run.
        """
        # Preamble
        contents = "#!/bin/bash\n"
        contents += "This script is automatically generated by artie-tool to test Artie's hardware functionality.\n"
        contents += "set -eu\n"

        # Each test step
        for test_def in self.steps:
            contents += self._convert_test_into_script(args, artie_id, test_def)

        return contents

    def create_job_def(self, args) -> None:
        """
        Create the k8s job def from all the information in the steps.
        """
        artie_id = self._determine_artie_id(args)
        delete_after_s = 1 * 24 * 60 * 60  # One day
        registry = self._determine_docker_registry(args)
        test_script_contents = self._determine_test_script_contents(args, artie_id)
        timeout_s = args.test_timeout_s
        version = self._determine_version(args)
        self.job_def = \
f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: artie-hw-test-job
  namespace: {kube.ArtieK8sValues.NAMESPACE}
  labels:
    app.kubernetes.io/component: hw-test
    app.kubernetes.io/version: {version}
    app.kubernetes.io/part-of: artie
    artie/artie-id: {artie_id}
  annotations:
spec:
  parallelism: 1
  completions: 1
  backoffLimit: 1
  activeDeadlineSeconds: {timeout_s}
  ttlSecondsAfterFinished: {delete_after_s}
  selector:
    matchLabels:
      app.kubernetes.io/component: hw-test
      app.kubernetes.io/version: {version}
      app.kubernetes.io/part-of: artie
      artie/artie-id: {artie_id}
  template:
    metadata:
      labels:
        app.kubernetes.io/component: hw-test
        app.kubernetes.io/version: {version}
        app.kubernetes.io/part-of: artie
        artie/artie-id: {artie_id}
      annotations:
    spec:
      containers:
        - name: artie-cli
          image: "{registry}/artie-cli:{version}"
          imagePullPolicy: Always
          command: ["/bin/bash", "-c", "/tests.sh"]
          env:
            - name: ARTIE_RUN_MODE
              value: production
            - name: ARTIE_ID
              value: "{artie_id}"
            - name: ARTIE_GIT_TAG
              value: "{version}"
            - name: LOG_COLLECTOR_HOSTNAME
              value: "log-collector-{artie_id}"
            - name: LOG_COLLECTOR_PORT
              value: "5170"
            - name: METRICS_SERVER_PORT
              value: "8090"
          volumeMounts:
            - mountPath: /tests.sh
              name: test-script
      volumes:
        - name: test-script
          configMap:
            name: test-script-configmap
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-script-configmap
  namespace: {kube.ArtieK8sValues.NAMESPACE}
  labels:
    app.kubernetes.io/component: hw-test
    app.kubernetes.io/version: {version}
    app.kubernetes.io/part-of: artie
    artie/artie-id: {artie_id}
  annotations:
data:
  tests.sh: |
    {test_script_contents}
"""

    def cleanup_job(self, args) -> None:
        """
        Clean up the k8s job if it is present on the cluster.
        """
        # TODO: Remove the job
        # TODO: Remove the configmap
        pass

class HardwareTestJob(test_job.TestJob):
    def __init__(self, steps: List[test_job.HWTest]) -> None:
        # Create a single super-step from the list of HWTests we are passed (to be compatable with the rest of the test infrastructure)
        single_step = CollectedHardwareTestSteps(steps)
        steps = [single_step]
        super().__init__(artifacts=[], steps=steps)
        self._single_step = single_step

    def setup(self, args):
        """
        """
        super().setup(args)
        # Define a k8s job on the single test step we have
        self._single_step.create_job_def(args)

    def teardown(self, args):
        """
        """
        if args.skip_teardown:
            common.info(f"--skip-teardown detected. There may be a k8s job and configmap on the cluster that need to be cleaned up manually.")
            return

        super().teardown(args)
        self._single_step.cleanup_job(args)
