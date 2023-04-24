from . import artifact
from . import dependency
from . import docker_build_job
from . import docker_compose_test_suite_job
from . import picofw_build_job
from . import single_container_cli_suite_job
from . import single_container_sanity_suite_job
from . import test_job
from . import yocto_build_job
from . import task
from .. import common
from dataclasses import dataclass
from enum import StrEnum
from enum import unique
from typing import Dict
from typing import List
from typing import Tuple
import collections
import glob
import os
import yaml

@unique
class TaskTypes(StrEnum):
    """
    These are the available types of tasks.
    """
    BUILD = "build"
    TEST = "test"
    FLASH = "flash"
    RELEASE = "release"

@dataclass
class CLIArg:
    """
    CLI Arg from YAML.
    """
    name: str
    default_val: str
    choices: List[str]
    arg_help: str

@dataclass
class TaskHeader:
    """
    Preamble common to each Task.
    """
    task_name: str
    labels: str
    dependencies: List[dependency.Dependency]
    artifacts: List[artifact.Artifact]
    cli_args: List[CLIArg]

def _replace_variables(s: str, fpath: str, key_value_pairs:Dict=None) -> str:
    """
    Replace any variables with their correct values.
    We can handle:
    - REPO_ROOT
    - GIT_TAG

    The other allowed keys are:
    - DUT
    - CLI

    which (if they are expected to be found) must be given, along with their values in the `key_value_pairs` args
    """
    if issubclass(type(s), dependency.Dependency):
        return s

    s = str(s)
    if '${REPO_ROOT}' in s:
        s = s.replace("${REPO_ROOT}", common.repo_root())

    if '${GIT_TAG}' in s:
        s = s.replace("${GIT_TAG}", common.git_tag())

    if '${DUT}' in s:
        if 'DUT' not in key_value_pairs:
            raise ValueError(f"No 'DUT' found in key_value_pairs {key_value_pairs}. This means either that ${{DUT}} is not allowed in this context in {fpath} or that this is a programmer error.")

        if issubclass(type(key_value_pairs['DUT']), dependency.Dependency):
            s = key_value_pairs['DUT']
            return s
        else:
            s = s.replace("${DUT}", key_value_pairs['DUT'])

    if '${CLI}' in s:
        if 'CLI' not in key_value_pairs:
            raise ValueError(f"No 'CLI' found in key_value_pairs {key_value_pairs}. This means either that ${{CLI}} is not allowed in this context in {fpath} or that this is a programmer error.")
        if issubclass(type(key_value_pairs['CLI']), dependency.Dependency):
            s = key_value_pairs['CLI']
            return s
        else:
            s = s.replace("${CLI}", key_value_pairs['CLI'])


    return s

def _validate_dict(config: Dict, key: str, val=None, keyerrmsg=None, valerrmsg=None):
    """
    Raises a `KeyError` if we can't find `key` in `config`.
    If `val` is non-None, we check to make sure that
    `config[key] == val`, raising a ValueError if not.
    In either case, if `errmsg` is non-None, we use that as the message
    in the exception, otherwise we use a generic error message.
    """
    if key not in config:
        msg = keyerrmsg if keyerrmsg is not None else f"Cannot find {key} in configuration"
        raise KeyError(msg)

    if val is not None and config[key] != val:
        msg = valerrmsg if valerrmsg is not None else f"config[{key}] != {val} in configuration"
        raise ValueError(msg)

def _import_single_dependency(config: Dict, fpath: str, key_value_pairs=None) -> dependency.Dependency:
    _validate_dict(config, 'dependency', keyerrmsg=f"Found an unexpected configuration when looking for 'dependency' in {fpath}")
    dep = config['dependency']
    _validate_dict(dep, 'name', keyerrmsg=f"No 'name' key found in dependency in {fpath}")
    _validate_dict(dep, 'producing-task', keyerrmsg=f"No 'producing-task' key found in dependency in {fpath}")
    matchexpr = dep.get('match', None)
    return dependency.Dependency(_replace_variables(dep['producing-task'], fpath, key_value_pairs), _replace_variables(dep['name'], fpath, key_value_pairs), matchexpr=matchexpr)

def _import_cli_args(config: Dict, fpath: str) -> List[CLIArg]:
    cli_args_list = config.get('cli-args', [])
    cli_args = []
    for arg_def in cli_args_list:
        _validate_dict(arg_def, 'name', keyerrmsg=f"No 'name' key found in one of the 'cli-args' definitions in {fpath}")
        name = _replace_variables(arg_def['name'], fpath)
        default_val = arg_def.get('default', None)
        arg_help = arg_def.get('help', None)
        choices = arg_def.get('choices', None)
        cli_args.append(CLIArg(
            name=name,
            default_val=_replace_variables(default_val, fpath) if default_val is not None else None,
            choices=[_replace_variables(choice, fpath) for choice in choices] if choices is not None else None,
            arg_help=_replace_variables(arg_help, fpath) if arg_help is not None else None
        ))
    return cli_args

def _import_artifacts_list(config: Dict, fpath: str, header_artifacts: List[artifact.Artifact]) -> List[artifact.Artifact]:
    """A list of artifacts that are names which refer to already imported artifacts."""
    def _get_artifact_from_name(name):
        for art in header_artifacts:
            if art.name == name:
                return art
        raise ValueError(f"'artifacts' list is asking for {name}, but can't find that artifact in the list of so-far imported artifacts: {header_artifacts}.")
    artifact_list = config.get('artifacts', [])
    artifacts = []
    for artname in artifact_list:
        art = _get_artifact_from_name(artname)
        artifacts.append(art)
    return artifacts

def _import_artifacts(config: Dict, fpath: str) -> List[artifact.Artifact]:
    artifact_list = config.get('artifacts', [])
    artifacts = []
    for artdef in artifact_list:
        _validate_dict(artdef, 'name', keyerrmsg=f"No 'name' key found in one of the 'artifacts' definitions in {fpath}")
        _validate_dict(artdef, 'type', keyerrmsg=f"No 'type' key found in one of the 'artifacts' definitions in {fpath}")
        artifact_name = _replace_variables(artdef['name'], fpath)
        producing_task_name = _replace_variables(config['name'], fpath)
        match artdef['type']:
            case 'yocto-image':
                art = artifact.YoctoImageArtifact(artifact_name, producing_task_name)
            case 'docker-image':
                art = artifact.DockerImageArtifact(artifact_name, producing_task_name)
            case 'fw-files':
                art = artifact.FilesArtifact(artifact_name, producing_task_name)
            case _:
                raise KeyError(f"Unrecognized Artifact type '{artdef['type']}' in {fpath}")
        artifacts.append(art)
    return artifacts

def _import_dependencies(config: Dict, fpath: str) -> List[dependency.Dependency]:
    dep_list = config.get('dependencies', [])
    for depdef in dep_list:
        if len(depdef.keys()) != 1 or len(depdef.values()) != 1:
            raise ValueError(f"'dependencies' section is mis-configured in {fpath}. Should be a list of <producing-task-name>: <artifact-name>")

    deps = []
    for depdef in dep_list:
        producing_task_name, artifact_name = [item for item in depdef.items()][0]  # Already asserted there should be exactly one item pair
        dep = dependency.Dependency(_replace_variables(producing_task_name, fpath), _replace_variables(artifact_name, fpath))
        deps.append(dep)
    return deps

def _import_labels(config: Dict, fpath: str) -> List[task.Labels]:
    label_list = config.get('labels', [])
    labels = []
    for label in label_list:
        match label:
            case task.Labels.DOCKER_IMAGE:
                labels.append(task.Labels.DOCKER_IMAGE)
            case task.Labels.FIRMWARE:
                labels.append(task.Labels.FIRMWARE)
            case task.Labels.YOCTO:
                labels.append(task.Labels.YOCTO)
            case task.Labels.BASE_IMAGE:
                labels.append(task.Labels.BASE_IMAGE)
            case task.Labels.STRESS:
                labels.append(task.Labels.STRESS)
            case task.Labels.UNIT:
                labels.append(task.Labels.UNIT)
            case task.Labels.INTEGRATION:
                labels.append(task.Labels.INTEGRATION)
            case task.Labels.SANITY:
                labels.append(task.Labels.SANITY)
            case task.Labels.TELEMETRY:
                labels.append(task.Labels.TELEMETRY)
            case _:
                raise ValueError(f"Unrecognized label '{label}' in 'labels' section of {fpath}")
    return labels

def _import_task_header(config: Dict, fpath: str) -> TaskHeader:
    _validate_dict(config, 'name')
    return TaskHeader(
        task_name=_replace_variables(config['name'], fpath),
        labels=_import_labels(config, fpath),
        dependencies=_import_dependencies(config, fpath),
        artifacts=_import_artifacts(config, fpath),
        cli_args=_import_cli_args(config, fpath),
    )

def _import_dependency_files(job_def: Dict, fpath: str) -> List[dependency.Dependency | str]:
    if 'dependency-files' not in job_def:
        return []

    depfiles = []
    depconfigs = job_def['dependency-files']
    for depconf in depconfigs:
        if type(depconf) == dict:
            dep = _import_single_dependency(depconf, fpath)
        else:
            dep = _replace_variables(depconf, fpath)
        depfiles.append(dep)
    return depfiles

def _import_build_args(job_def: Dict, fpath: str) -> List[docker_build_job.DockerBuildArg]:
    if 'build-args' not in job_def:
        return []

    args = []
    build_args_def = job_def['build-args']
    for build_arg in build_args_def:
        assert len([k for k in build_arg.keys()]) == 1, f"build-arg is misconfigured: {build_arg} in {fpath}"
        key, value = [(k, v) for k, v in build_arg.items()][0]
        if type(value) == dict:
            dep = _import_single_dependency(value, fpath)
            args.append(docker_build_job.DockerBuildArg(_replace_variables(key, fpath), dep))
        else:
            args.append(docker_build_job.DockerBuildArg(_replace_variables(key, fpath), _replace_variables(value, fpath)))
    return args

def _import_docker_build_common(job_def: Dict, fpath: str, errmsg_section: str, header: TaskHeader) -> collections.namedtuple:
    _validate_dict(job_def, 'artifacts', keyerrmsg=f"Could not find 'artifacts' section in '{errmsg_section}' in {fpath}")
    _validate_dict(job_def, 'img-base-name', keyerrmsg=f"Could not find 'img-base-name' section in '{errmsg_section}' in {fpath}")
    _validate_dict(job_def, 'dockerfile-dpath', keyerrmsg=f"Could not find 'dockerfile-dpath' section in '{errmsg_section}' in {fpath}")
    artifacts = _import_artifacts_list(job_def, fpath, header.artifacts)
    img_base_name = _replace_variables(job_def['img-base-name'], fpath)
    buildx = job_def.get('buildx', False)
    dockerfile_dpath = _replace_variables(job_def['dockerfile-dpath'], fpath)
    dockerfile = _replace_variables(job_def.get('dockerfile', "Dockerfile"), fpath)
    build_context = _replace_variables(job_def.get('build-context', '.'), fpath)
    dependency_files = _import_dependency_files(job_def, fpath)
    build_args = _import_build_args(job_def, fpath)
    Config = collections.namedtuple('Config', ["artifacts", "img_base_name", "buildx", "dockerfile_dpath", "dockerfile", "build_context", "dependency_files", "build_args"])
    return Config(artifacts, img_base_name, buildx, dockerfile_dpath, dockerfile, build_context, dependency_files, build_args)

def _import_docker_build_job(job_def: Dict, fpath: str, header: TaskHeader) -> docker_build_job.DockerBuildJob:
    config = _import_docker_build_common(job_def, fpath, "docker-build", header)
    return docker_build_job.DockerBuildJob(
        artifacts=config.artifacts,
        img_base_name=config.img_base_name,
        dockerfile_dpath=config.dockerfile_dpath,
        buildx=config.buildx,
        dockerfile=config.dockerfile,
        build_context=config.build_context,
        dependency_files=config.dependency_files,
        build_args=config.build_args
    )

def _import_fw_build_job(job_def: Dict, fpath: str, header: TaskHeader) -> picofw_build_job.PicoFWBuildJob:
    config = _import_docker_build_common(job_def, fpath, "fw-build", header)
    _validate_dict(job_def, 'fw-files-in-container', keyerrmsg=f"'fw-files-in-container' section missing from 'fw-build' section in {fpath}")
    fw_files_in_container = [_replace_variables(f, fpath) for f in job_def['fw-files-in-container']]
    return picofw_build_job.PicoFWBuildJob(
        artifacts=config.artifacts,
        img_base_name=config.img_base_name,
        dockerfile_dpath=config.dockerfile_dpath,
        fw_files_in_container=fw_files_in_container,
        buildx=config.buildx,
        dockerfile=config.dockerfile,
        build_context=config.build_context,
        dependency_files=config.dependency_files,
        build_args=config.build_args
    )

def _import_yocto_build_job(job_def: Dict, fpath: str, header: TaskHeader) -> yocto_build_job.YoctoBuildJob:
    _validate_dict(job_def, 'artifacts', keyerrmsg=f"Could not find 'artifacts' section in 'yocto-build-job' in {fpath}")
    _validate_dict(job_def, 'repo', keyerrmsg=f"Could not find 'repo' section in 'yocto-build-job' in {fpath}")
    _validate_dict(job_def, 'script', keyerrmsg=f"Could not find 'script' section in 'yocto-build-job' in {fpath}")
    _validate_dict(job_def, 'binary-fname', keyerrmsg=f"Could not find 'binary-fname' section in 'yocto-build-job' in {fpath}")
    artifacts = _import_artifacts_list(job_def, fpath, header.artifacts)
    repo = _replace_variables(job_def['repo'], fpath)
    script = job_def['script']  # We do not allow YAML-level variable expansion here
    binary_fname = _replace_variables(job_def['binary-fname'], fpath)
    return yocto_build_job.YoctoBuildJob(
        artifacts=artifacts,
        repo=repo,
        script=script,
        binary_fname=binary_fname
    )

def _import_build_task(header: TaskHeader, steps_configs: List[Dict], fpath: str) -> task.BuildTask:
    jobs = []
    for job_def in steps_configs:
        _validate_dict(job_def, 'job', keyerrmsg=f"No 'job' key found in job description in 'steps' section of {fpath}")
        match job_def['job']:
            case 'yocto-build':
                jobs.append(_import_yocto_build_job(job_def, fpath, header))
            case 'docker-build':
                jobs.append(_import_docker_build_job(job_def, fpath, header))
            case 'pico-fw-build':
                jobs.append(_import_fw_build_job(job_def, fpath, header))
            case _:
                raise ValueError(f"Unrecognized 'job' type: '{job_def['job']}' in {fpath}")

    return task.BuildTask(
        name=header.task_name,
        labels=header.labels,
        dependencies=header.dependencies,
        artifacts=header.artifacts,
        jobs=jobs,
        cli_args=header.cli_args
    )

def _import_sanity_test_job(job_def: Dict, fpath: str) -> single_container_sanity_suite_job.SingleContainerSanitySuiteJob:
    _validate_dict(job_def, 'steps', keyerrmsg=f"Missing 'steps' section in 'single-container-sanity-suite' definition in {fpath}")
    sanity_test_steps = []
    steps_def = job_def['steps']
    for sdef in steps_def:
        _validate_dict(sdef, 'test-name', keyerrmsg=f"Missing 'test-name' from 'steps' section in {fpath}")
        _validate_dict(sdef, 'docker-image-under-test', keyerrmsg=f"Missing 'docker-image-under-test' from 'steps' section in {fpath}")
        _validate_dict(sdef, 'cmd-to-run-in-dut', keyerrmsg=f"Missing 'cmd-to-run-in-dut' from 'steps' section in {fpath}")
        dut = _replace_variables(sdef['docker-image-under-test'], fpath) if type(sdef['docker-image-under-test']) != dict else _import_single_dependency(sdef['docker-image-under-test'], fpath)
        test_name = _replace_variables(sdef['test-name'], fpath, {"DUT": dut})
        cmd_to_run_in_dut = _replace_variables(sdef['cmd-to-run-in-dut'], fpath, {"DUT": dut})
        test_step = single_container_sanity_suite_job.SanityTest(test_name, dut, cmd_to_run_in_dut)
        sanity_test_steps.append(test_step)
    return single_container_sanity_suite_job.SingleContainerSanitySuiteJob(sanity_test_steps)

def _import_expected_outputs(config: Dict, fpath: str, key_value_pairs: Dict) -> List[test_job.ExpectedOutput]:
    expected_outputs_def = config['expected-outputs']
    expected_outputs = []
    for expected_output in expected_outputs_def:
        _validate_dict(expected_output, 'what', keyerrmsg=f"Missing 'what' key in 'expected-outputs' in {fpath}")
        _validate_dict(expected_output, 'where', keyerrmsg=f"Missing 'where' key in 'expected-outputs' in {fpath}")
        what = _replace_variables(expected_output['what'], fpath, key_value_pairs)
        where = _replace_variables(expected_output['where'], fpath, key_value_pairs)
        is_cli = expected_output['where'].strip() == "${CLI}"
        e = test_job.ExpectedOutput(what, where, cli=is_cli)
        expected_outputs.append(e)
    return expected_outputs

def _import_unit_test_job(job_def: Dict, fpath: str) -> test_job.CLITest:
    _validate_dict(job_def, 'steps', keyerrmsg=f"Missing 'steps' section in 'single-container-cli-suite' definition in {fpath}")
    _validate_dict(job_def, 'docker-image-under-test', keyerrmsg=f"Missing 'docker-image-under-test' in {fpath}")
    _validate_dict(job_def, 'cmd-to-run-in-dut', keyerrmsg=f"Missing 'cmd-to-run-in-dut' in {fpath}")
    _validate_dict(job_def, 'cli-image', keyerrmsg=f"Missing 'cli-image' key in {fpath}")
    dut = _replace_variables(job_def['docker-image-under-test'], fpath) if type(job_def['docker-image-under-test']) != dict else _import_single_dependency(job_def['docker-image-under-test'], fpath)
    cli_image = _replace_variables(job_def['cli-image'], fpath, {'DUT': dut}) if type(job_def['cli-image']) != dict else _import_single_dependency(job_def['cli-image'], fpath)
    cmd_to_run_in_dut = _replace_variables(job_def['cmd-to-run-in-dut'], fpath, {'DUT': dut})
    dut_port_mappings = {k: v for mapping in job_def.get('dut-port-mappings', []) for k, v in mapping.items()}
    cli_test_steps = []
    steps_def = job_def['steps']
    for sdef in steps_def:
        _validate_dict(sdef, 'test-name', keyerrmsg=f"Missing 'test-name' from 'steps' section in {fpath}")
        _validate_dict(sdef, 'cmd-to-run-in-cli', keyerrmsg=f"Missing 'cmd-to-run-in-cli' from 'steps' section in {fpath}")
        _validate_dict(sdef, 'expected-outputs', keyerrmsg=f"Missing 'expected-outputs' section from 'steps' section in {fpath}")
        test_name = _replace_variables(sdef['test-name'], fpath, {"DUT": dut, "CLI": cli_image})
        cli_cmd = _replace_variables(sdef['cmd-to-run-in-cli'], fpath, {"DUT": dut})
        expected_outputs = _import_expected_outputs(sdef, fpath, {'DUT': dut, 'CLI': cli_image})
        cli_test_steps.append(test_job.CLITest(test_name, cli_image, cli_cmd, expected_outputs))
    return single_container_cli_suite_job.SingleContainerCLISuiteJob(cli_test_steps, dut, cmd_to_run_in_dut, dut_port_mappings)

def _import_docker_compose_variables(config: Dict, fpath: str, cli: str) -> List[Tuple[str, str]]:
    variable_def_list = config.get('compose-docker-image-variables', [])
    for vardef in variable_def_list:
        if len(vardef.keys()) != 1 or len(vardef.values()) != 1:
            raise ValueError(f"'compose-docker-image-variables' section is mis-configured in {fpath}. Should be a list of <value-to-replace-in-file>: <value or dependency definition>")

    variables = []
    for vardef in variable_def_list:
        varname, var = [item for item in vardef.items()][0]  # Already asserted there should be exactly one item pair
        if type(var) == dict:
            var = _import_single_dependency(var, fpath, {'CLI': cli})
        else:
            var = _replace_variables(var, fpath, {'CLI': cli})
        variables.append((varname, var))
    return variables

def _import_integration_test_job(job_def: Dict, fpath: str) -> docker_compose_test_suite_job.DockerComposeTestSuiteJob:
    _validate_dict(job_def, 'steps', keyerrmsg=f"Missing 'steps' section in 'docker-compose-test-suite' definition in {fpath}")
    _validate_dict(job_def, 'compose-fname', keyerrmsg=f"Missing 'compose-fname' in 'docker-compose-test-suite' definition in {fpath}")
    _validate_dict(job_def, 'cli-image', keyerrmsg=f"Missing 'cli-image' definition in 'docker-compose-test-suite' definition in {fpath}")
    compose_fname = job_def['compose-fname']
    cli_image = _replace_variables(job_def['cli-image'], fpath) if type(job_def['cli-image']) != dict else _import_single_dependency(job_def['cli-image'], fpath)
    compose_docker_image_variables = _import_docker_compose_variables(job_def, fpath, cli_image)
    cli_test_steps = []
    steps_def = job_def['steps']
    for sdef in steps_def:
        _validate_dict(sdef, 'test-name', keyerrmsg=f"Missing 'test-name' from 'steps' section in {fpath}")
        _validate_dict(sdef, 'cmd-to-run-in-cli', keyerrmsg=f"Missing 'cmd-to-run-in-cli' from 'steps' section in {fpath}")
        _validate_dict(sdef, 'expected-outputs', keyerrmsg=f"Missing 'expected-outputs' section from 'steps' section in {fpath}")
        test_name = _replace_variables(sdef['test-name'], fpath, {"CLI": cli_image})
        cli_cmd = _replace_variables(sdef['cmd-to-run-in-cli'], fpath, {"CLI": cli_image})
        expected_outputs = _import_expected_outputs(sdef, fpath, {'CLI': cli_image})
        cli_test_steps.append(test_job.CLITest(test_name, cli_image, cli_cmd, expected_outputs))
    return docker_compose_test_suite_job.DockerComposeTestSuiteJob(cli_test_steps, compose_fname, compose_docker_image_variables)

def _import_test_task(header: TaskHeader, steps_configs: List[Dict], fpath: str) -> task.TestTask:
    jobs = []
    for job_def in steps_configs:
        _validate_dict(job_def, 'job', keyerrmsg=f"No 'job' key found in job description in 'steps' section of {fpath}")
        match job_def['job']:
            case 'single-container-sanity-suite':
                jobs.append(_import_sanity_test_job(job_def, fpath))
            case 'single-container-cli-suite':
                jobs.append(_import_unit_test_job(job_def, fpath))
            case 'docker-compose-test-suite':
                jobs.append(_import_integration_test_job(job_def, fpath))
            case _:
                raise ValueError(f"Unrecognized 'job' type: '{job_def['job']}' in {fpath}")

    return task.TestTask(
        name=header.task_name,
        labels=header.labels,
        dependencies=header.dependencies,
        artifacts=header.artifacts,
        jobs=jobs,
        cli_args=header.cli_args
    )

def _import_task(fpath: str) -> task.Task:
    """
    Import a `Task` subclass from the given `fpath` configuration file.
    """
    try:
        with open(fpath, 'r') as f:
            task_config = yaml.load(f, yaml.FullLoader)

        _validate_dict(task_config, 'type')
        _validate_dict(task_config, 'steps')
        task_type = task_config['type']
        task_header = _import_task_header(task_config, fpath)
        match task_type:
            case TaskTypes.BUILD:
                return _import_build_task(task_header, task_config['steps'], fpath)
            case TaskTypes.TEST:
                return _import_test_task(task_header, task_config['steps'], fpath)
            case TaskTypes.FLASH:
                raise NotImplementedError("Have not implemented flash tasks yet")
            case TaskTypes.RELEASE:
                raise NotImplementedError("Have not implemented release tasks yet")
            case _:
                raise ValueError(f"Unrecognized 'type' value in {fpath}: {task_type}")
    except Exception as e:
        print(f"Cannot import {fpath}: {e}")
        raise e

def import_tasks(dpath: str) -> List[task.Task]:
    """
    Import all tasks that we find in the given directory, recursively
    and return them as a list of `Task` subclasses.
    """
    fpaths = glob.glob(os.path.join(dpath, "**", "*.yaml"), recursive=True)
    task_to_yaml_dict = {}
    tasks = []
    for fpath in fpaths:
        t = _import_task(fpath)
        if t.name in task_to_yaml_dict:
            raise FileExistsError(f"Already have a task with the name {t.name}. Task names must be unique. Offending YAML files: {fpath} and {task_to_yaml_dict[t.name]}")
        else:
            task_to_yaml_dict[t.name] = fpath
            tasks.append(t)
    return tasks
