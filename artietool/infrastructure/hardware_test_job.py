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
a job and two config maps. The job runs two scripts - a shell script that is dynamically created - and
a Python script that interprets the output of the each step in the shell script. Both of these scripts
are mapped into the container via the config maps.
The job's container is just the normal Artie CLI container, so we need to use the config map to get
the shell script, which is created dynamically, and the Python script, which should change as a function of
the test infrastructure version - not as a function of Artie CLI's version, into the container.

The shell test script is composed dynamically by adding each test piped into
an interpretation script. The result is something that looks like this:

artie-cli eyebrows status self-check --artie-id artie-001 | python interpret_test_output.py
artie-cli mouth status self-check --artie-id artie-001 | python interpret_test_output.py
artie-cli reset status self-check --artie-id artie-001 | python interpret_test_output.py
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
import os
import time

class CollectedHardwareTestSteps:
    """
    The logic that we run inside the single hardware test job.
    """
    def __init__(self, steps: List[test_job.HWTest]) -> None:
        self.steps = steps
        self.job_def = None  # Filled in during test setup
        self.job_name = None  # Filled in during __call__
        self.test_script_configmap_name = None  # Filled in during __call__
        self.test_script_configmap_def = None  # Filled in during test setup
        self.interpret_test_script_configmap_name = None  # Filled in during __call__
        self.interpret_test_script_configmap_def = None  # Filled in during test setup
        self.test_name = "Hardware Tests"

    def _launch_k8s_job(self, args):
        common.info("Creating config map for test script...")
        test_script_configmap = kube.create_from_yaml(args, self.test_script_configmap_def)
        self.test_script_configmap_name = test_script_configmap.metadata.name
        common.info("Creating config map for interpretation script...")
        interpret_script_configmap = kube.create_from_yaml(args, self.interpret_test_script_configmap_def)
        self.interpret_test_script_configmap_name = interpret_script_configmap.metadata.name
        common.info("Launching the test job itself...")
        job = kube.create_from_yaml(args, self.job_def)
        self.job_name = job.metadata.name

    def __call__(self, args) -> result.TestResult:
        # Launch the k8s job
        common.info(f"Launching k8s test job...")
        self._launch_k8s_job(args)

        # Check the job status
        common.info("Waiting until K8s test job completes...")
        status = kube.check_job_status(args, self.job_name)
        while status == kube.JobStatuses.INCOMPLETE or status == kube.JobStatuses.UNKNOWN:
            time.sleep(5)
            status = kube.check_job_status(args, self.job_name)

        job_status = kube.check_job_status(args, self.job_name)
        if job_status == kube.JobStatuses.FAILED:
            common.error(f"HW Job failed, the logs from the HW test job follow:")
            kube.log_job_results(args, self.job_name)
            return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=result.TestStatuses.FAIL)
        elif job_status == kube.JobStatuses.SUCCEEDED:
            return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=result.TestStatuses.SUCCESS)
        else:
            common.error(f"HW Job has unrecognized status: {job_status}")
            return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=result.TestStatuses.FAIL)

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
        contents = ""
        for test_cmd in test_def.cmds_to_run_in_cli:
          # E.g. artie-cli eyebrows status self-check --artie-id artie-001
          cmd = test_cmd + f" --artie-id {artie_id}"

          # We run the command and pipe it into the interpret script
          contents += f"{cmd} | tee >(python /interpret_test_output.py)\n"

        return contents

    def _determine_test_script_contents(self, args, artie_id: str, leading_spaces: int) -> str:
        """
        Returns the contents of the script the CLI image job will run.
        """
        # Preamble
        contents = "#!/bin/bash\n"
        contents += "# This script is automatically generated by artie-tool to test Artie's hardware functionality.\n"
        contents += "set -euo pipefail\n"

        # Each test step
        for test_def in self.steps:
            contents += self._convert_test_into_script(args, artie_id, test_def)

        indented_contents = ""
        for line in contents.splitlines():
            indented_contents += " " * leading_spaces + line.rstrip() + "\n"
        return indented_contents

    def _get_contents_of_interpret_test_script(self, leading_spaces: int):
      """
      Get the contents of the script that interprets the output of a test.
      """
      fpath = os.path.join(common.repo_root(), "artietool", "test", "interpret_test_output.py")
      if not os.path.isfile(fpath):
          raise FileNotFoundError(f"Cannot find interpret_test_output.py, which should be found at {fpath}")

      with open(fpath, 'r') as f:
          contents = f.readlines()

      return '\n'.join([" " * leading_spaces + line.rstrip() for line in contents])  # Remove the carriage return if there is one and replace with simple newline

    def create_job_def(self, args) -> None:
        """
        Create the k8s job def from all the information in the steps.
        """
        artie_id = self._determine_artie_id(args)
        delete_after_s = 1 * 24 * 60 * 60  # One day
        registry = self._determine_docker_registry(args)
        interpret_test_output_contents = self._get_contents_of_interpret_test_script(leading_spaces=4)
        test_script_contents = self._determine_test_script_contents(args, artie_id, leading_spaces=4)
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
              subPath: tests.sh
              name: test-script
            - mountPath: /interpret_test_output.py
              subPath: interpret_test_output.py
              name: interpret-script
      volumes:
        - name: test-script
          configMap:
            name: test-script-configmap
            defaultMode: 0777
        - name: interpret-script
          configMap:
            name: interpret-script-configmap
            defaultMode: 0777
      restartPolicy: Never
"""

        self.test_script_configmap_def = \
f"""
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
        self.interpret_test_script_configmap_def = \
f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: interpret-script-configmap
  namespace: {kube.ArtieK8sValues.NAMESPACE}
  labels:
    app.kubernetes.io/component: hw-test
    app.kubernetes.io/version: {version}
    app.kubernetes.io/part-of: artie
    artie/artie-id: {artie_id}
  annotations:
data:
  interpret_test_output.py: |
{interpret_test_output_contents}
"""

    def cleanup_job(self, args) -> None:
        """
        Clean up the k8s job if it is present on the cluster.
        """
        # Remove the job and its config maps
        if self.job_name is not None:  # If we don't have a job_name, we didn't ever actually create the job
            kube.delete_job(args, self.job_name)

        if self.test_script_configmap_name is not None:
            kube.delete_configmap(args, self.test_script_configmap_name)

        if self.interpret_test_script_configmap_name is not None:
            kube.delete_configmap(args, self.interpret_test_script_configmap_name)

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
            common.info(f"--skip-teardown detected. There may be a k8s job and configmaps on the cluster that need to be cleaned up manually.")
            return

        super().teardown(args)
        self._single_step.cleanup_job(args)
