"""
All machinery releated to unit testing and whatnot.
"""
from .. import common
from .. import docker
from ..build import build
from ..infrastructure import artifact
from ..infrastructure import result
from ..infrastructure import run
from ..infrastructure import task
from ..infrastructure import task_importer
from typing import Iterable, List
import argparse
import datetime
import os
import traceback
import xml.etree.ElementTree as ET

# Test tasks come from every component in the workspace - see test_tasks().
_TEST_TASKS = None

def test_tasks():
    """
    Every test task in the workspace, discovered once per process.

    Each component owns the definitions of its own tasks, so this looks across every
    checkout rather than reading one directory. Deferred until first use so that a
    malformed task definition in any component cannot break `--help` at import time.
    """
    global _TEST_TASKS
    if _TEST_TASKS is None:
        _TEST_TASKS = task_importer.discover_tasks("test")
    return _TEST_TASKS

TEST_CLASSES = [
    "all",
    "all-sanity",
    "all-unit",
    "all-integration",
    "all-stress",
    "all-fw",
    "all-containers",
    "all-yocto",
    "all-hw",
    "all-library",
]

def _create_test_folder_tag(args) -> str:
    """
    Creates tag for the test output subfolder. It uses the Docker tag passed in by the user if present
    (after sanitizing it) or else uses the git hash.
    """
    tag = args.docker_tag if hasattr(args, 'docker_tag') and args.docker_tag else common.git_tag()
    tag = "".join(c for c in tag if c.isalnum() or c in "._-")
    return tag

def _combine_hw_tests(tasks: task.Task) -> List[task.Task]:
    """
    Combine all HW tests into a single one and return the resulting,
    modified list of all tasks.
    """
    hw_tasks = [t for t in tasks if task.Labels.HARDWARE in t.labels]
    if len(hw_tasks) > 1:
        common.info("Combining all hardware test tasks into a single one")
        for t in hw_tasks[1:]:
            hw_tasks[0].combine(t)
        hw_tasks = [hw_tasks[0]]
    return [t for t in tasks if task.Labels.HARDWARE not in t.labels] + hw_tasks

def _test_class_of_items(args):
    """
    Choose between the different categories and run one.
    """
    tasks = []
    match args.module:
        case "all":
            tasks = [t for t in test_tasks() if task.Labels.HARDWARE not in t.labels] if args.include_yocto else [t for t in test_tasks() if task.Labels.YOCTO not in t.labels and task.Labels.HARDWARE not in t.labels]
        case "all-fw":
            tasks = [t for t in test_tasks() if task.Labels.FIRMWARE in t.labels]
        case "all-containers":
            tasks = [t for t in test_tasks() if task.Labels.DOCKER_IMAGE in t.labels]
        case "all-yocto":
            tasks = [t for t in test_tasks() if task.Labels.YOCTO in t.labels]
        case "all-stress":
            tasks = [t for t in test_tasks() if task.Labels.STRESS in t.labels]
        case "all-unit":
            tasks = [t for t in test_tasks() if task.Labels.UNIT in t.labels]
        case "all-integration":
            tasks = [t for t in test_tasks() if task.Labels.INTEGRATION in t.labels]
        case "all-sanity":
            tasks = [t for t in test_tasks() if task.Labels.SANITY in t.labels]
        case "all-hw":
            tasks = [t for t in test_tasks() if task.Labels.HARDWARE in t.labels]
        case "all-library":
            tasks = [t for t in test_tasks() if task.Labels.LIBRARY in t.labels]
        case _:
            raise ValueError(f"{args.module} is invalid for some reason")

    # All hardware test tasks need to be combined into a single test task
    tasks = _combine_hw_tests(tasks)

    # Run them and return the results
    return run.run_tasks(args, tasks, test_tasks() + build.build_tasks())

def _write_results_to_output_folder(args, res: result.TaskResult, dpath):
    """
    Writes the results to a folder inside dpath.
    """
    fpath = os.path.join(dpath, f"{res.name}.txt")
    with open(fpath, 'w') as f:
        f.write(res.to_verbose_str())
        f.write(os.linesep)
        f.write("------------------------------------")
        f.write(os.linesep)
        # Test `TaskResult` objects have one or more JobResults.
        # Each JobResult has one or more TestResults in its 'artifacts' field.
        testresults = []
        for j in res.job_results:
            for r in j.artifacts:
                if issubclass(type(r), result.TestResult):
                    testresults.append(r)
        for testresult in testresults:
            f.writelines(testresult.to_verbose_str())

def _collect_test_results(res) -> List[result.TestResult]:
    """
    Pull the individual TestResult objects out of a TaskResult (they live in
    each JobResult's artifacts field).
    """
    testresults = []
    for j in getattr(res, 'job_results', []):
        for r in getattr(j, 'artifacts', []):
            if issubclass(type(r), result.TestResult):
                testresults.append(r)
    return testresults

def _write_junit_xml(results, fpath):
    """
    Write all test results to a JUnit XML file so CI systems can ingest per-test outcomes.
    """
    testsuites = ET.Element("testsuites")
    for res in results:
        suite = ET.SubElement(testsuites, "testsuite", name=res.name)
        ntests = nfailures = nskipped = nerrors = 0
        testresults = _collect_test_results(res)
        if testresults:
            for tr in testresults:
                ntests += 1
                case = ET.SubElement(suite, "testcase", name=tr.name, classname=tr.producing_task_name if tr.producing_task_name else res.name)
                if tr.status == result.TestStatuses.FAIL:
                    nfailures += 1
                    failure = ET.SubElement(case, "failure", message=str(tr.msg) if tr.msg else "Test failed")
                    if tr.exception:
                        failure.text = os.linesep.join(traceback.format_exception(tr.exception))
                elif tr.status == result.TestStatuses.DID_NOT_RUN:
                    nskipped += 1
                    ET.SubElement(case, "skipped")
        else:
            # A task that produced no individual test results still gets one testcase so its status is visible
            ntests += 1
            case = ET.SubElement(suite, "testcase", name=res.name, classname=res.name)
            if not res.success:
                nerrors += 1
                error = ET.SubElement(case, "error", message="Task failed without producing individual test results")
                if getattr(res, 'error', None):
                    error.text = str(res.error)
        suite.set("tests", str(ntests))
        suite.set("failures", str(nfailures))
        suite.set("skipped", str(nskipped))
        suite.set("errors", str(nerrors))

    dpath = os.path.dirname(os.path.abspath(fpath))
    os.makedirs(dpath, exist_ok=True)
    ET.ElementTree(testsuites).write(fpath, encoding="utf-8", xml_declaration=True)

def test(args):
    """
    Top-level test function.
    """
    # Potentially clean first
    if args.clean:
        common.clean()

    if args.module.startswith("all"):
        results, ran_tasks = _test_class_of_items(args)
    else:
        test_task = common.find_task_from_name(args.module, test_tasks())
        assert test_task is not None, f"Somehow test_task is None (args.module: {args.module})"
        results, ran_tasks = run.run_tasks(args, [test_task], test_tasks() + build.build_tasks())

    # Clean up after ourselves
    for t in ran_tasks:
        t.clean(args)
    docker.clean_docker_containers()

    # Create the results output folder
    if not os.path.isdir(args.results_folder):
        os.makedirs(args.results_folder)

    # Create a time-stamped subfolder inside the results folder
    timestamp = datetime.datetime.now().strftime("%y-%b-%d-%H.%M")
    git_tag = _create_test_folder_tag(args)
    subfolder_dpath = os.path.join(args.results_folder, f"{timestamp}-{git_tag}")
    if os.path.isdir(subfolder_dpath):
        common.error(f"Can't create log results because {subfolder_dpath} is already a folder somehow.")
    else:
        os.makedirs(subfolder_dpath)

    # Print the results for human consumption
    retcode = 0
    if isinstance(results, Iterable):
        results = sorted(results, key=lambda r: r.name)
        for result in results:
            print(result)
            _write_results_to_output_folder(args, result, subfolder_dpath)
            if not result.success:
                retcode = 1
    else:
        _write_results_to_output_folder(args, result, subfolder_dpath)
        print(results)
        if not results.success:
            retcode = 1

    # Write a JUnit XML report if requested
    if args.junit_xml:
        _write_junit_xml(results if isinstance(results, Iterable) else [results], args.junit_xml)
        common.info(f"Wrote JUnit XML test report to {args.junit_xml}")

    # Clean the tmp folder and whatever else (not build artifacts though)
    common.clean_build_stuff()

    return retcode

def fill_subparser(parser_test: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser_test.add_subparsers(title="test-module", description="Choose which module to run tests on")

    # Args that are useful for all test tasks
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("Test", "Test Options")
    group.add_argument("--clean", action='store_true', help="If given, we will run a 'clean' action first, then test.")
    group.add_argument("-f", "--force-completion", action='store_true', help="Force all tests in a single task to run, even if one of them fails.")
    group.add_argument("--include-yocto", action='store_true', help="When testing with 'all', we typically exclude Yocto images. Use this flag if you want to include them in 'all'.")
    group.add_argument("--results-folder", default=common.default_test_results_location())
    group.add_argument("--test-timeout-s", default=120, type=int, help="Default timeout for all tests.")
    group.add_argument("--junit-xml", default=None, type=str, help="If given, we write a JUnit XML report of all test results to this file path (for CI systems).")
    group.add_argument("--skip-teardown", action='store_true', help="If given, we do not tear down the Docker compose project(s) in the case of a failure - useful for debugging.")

    # Add the all* classes of tasks
    for name in TEST_CLASSES:
        task_parser = subparsers.add_parser(name, parents=[option_parser])
        task_parser.set_defaults(cmd=test, module=name)

    # Add all the tests
    for t in test_tasks():
        task_parser = subparsers.add_parser(t.name, parents=[option_parser])
        t.fill_subparser(task_parser, option_parser)        # Fill argparse with anything that is specific to the task
        task_parser.set_defaults(cmd=test, module=t.name)   # Regardless of the task chosen, the command is always 'test' from this module
