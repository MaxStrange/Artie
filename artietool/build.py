"""
All the machinery for building.
"""
from . import common
from . import fw_eyebrows
from . import fw_mouth
from . import container_eyebrows_driver
from . import container_mouth_driver
from . import yocto_controller_module
from collections.abc import Iterable
import argparse
import logging
import multiprocessing
import traceback

BUILD_TASKS = []
BUILD_TASKS += fw_eyebrows.BUILD_CHOICES
BUILD_TASKS += fw_mouth.BUILD_CHOICES
BUILD_TASKS += container_eyebrows_driver.BUILD_CHOICES
BUILD_TASKS += container_mouth_driver.BUILD_CHOICES
BUILD_TASKS += yocto_controller_module.BUILD_CHOICES

# Conventions:
# * Use "all-" for items that build all of a class of something
# * Use "fw-" for MCU FW items
# * Use "container-" for container items
# * Use "yocto-" for Yocto images
BUILD_CHOICES = [
    "all",
    "all-fw",
    "all-containers",
    "all-yocto",
] + [task.name for task in BUILD_TASKS]

class FuncWrapper:
    def __init__(self, func, q: multiprocessing.Queue, worker_index: int):
        self._func = func
        self._q = q
        self._worker_index = worker_index

    def __call__(self, args):
        try:
            result = self._func(args)
        except Exception as e:
            name = multiprocessing.current_process().name
            result = common.BuildResult(name=name, success=False, error=e)
            if args.enable_error_tracing:
                logging.error(f"Error running build task {name}: {''.join(traceback.format_exception(e))}")
        self._q.put((self._worker_index, result))

def _find_task_from_name(name: str) -> common.BuildTask:
    """
    Finds and retrieves the BuildTask from the BUILD_TASKS list from its name.

    Returns None if can't find it.
    """
    for task in BUILD_TASKS:
        if task.name == name:
            return task
    return None

def _check_tasks_against_dependencies(args, build_tasks):
    """
    Check each build task against args._artifacts to see
    if anything is ready to run. If so, return the index of it.
    If nothing is found, return None.
    """
    for i, task in enumerate(build_tasks):
        if not task.dependencies:
            # This task has no dependencies, we can run it
            logging.info(f"Found a ready task: {task.name}")
            return i

        ready = True
        for depname, depitems in task.dependencies.items():
            if depname not in args._artifacts:
                # This task has at least one dependency that has not been run
                ready = False
                break

            # Sanity check that each required item was actually built
            for item in depitems:
                if item not in args._artifacts[depname]:
                    logging.error(f"Build task {task} depends on {depname}'s {item}, but even though {depname} has run, {item} was not produced. Attempting to build anyway.")

        if ready:
            # This task has all of its dependencies built already.
            logging.info(f"Found a ready task: {task.name}")
            return i

    # Couldn't find one
    return None

def _build_all_multiprocess(args, build_tasks):
    """
    Run the given `build_tasks`, each with `args` in parallel, using however many
    maximum processes have been specified in `args` (which may be 1).
    """
    # Allow build tasks to retrieve artifacts from other build tasks
    setattr(args, "_artifacts", {})

    ntasks = len(build_tasks)
    results = []
    workers = [None for _ in range(min(args.nprocs, ntasks))]
    q = multiprocessing.Queue()
    tasks_we_ran = []
    while len(results) != ntasks:
        have_capacity = None in workers
        still_work_to_do = len(build_tasks) > 0

        if have_capacity and still_work_to_do:
            task_ready_index = _check_tasks_against_dependencies(args, build_tasks)
        else:
            task_ready_index = None

        if have_capacity and still_work_to_do and task_ready_index is not None:
            # Create a new worker to do some work
            worker_index = workers.index(None)
            build_task = build_tasks.pop(task_ready_index)
            tasks_we_ran.append(build_task)
            p = multiprocessing.Process(target=FuncWrapper(build_task.build_function, q, worker_index), args=(args,), name=build_task.name, daemon=True)
            workers[worker_index] = p
            workers[worker_index].start()
        else:
            # Otherwise, sleep until at least one worker is done
            # When that worker is done, collect its results and terminate the worker process
            worker_index, result = q.get()
            results.append(result)
            workers[worker_index].join()
            workers[worker_index] = None
            # Append artifacts to args so that dependent tasks can access them
            args._artifacts[result.name] = {name: value for name, value in result.artifacts.items()}
            logging.info(f"Task {result.name} finished.")
    return results, tasks_we_ran

def _recurse_dependencies(args, task, remaining_tasks, updated_tasks):
    if task.dependencies is not None:
        for name in task.dependencies:
            dep_task = _find_task_from_name(name)
            if dep_task in remaining_tasks or dep_task in updated_tasks:
                # Duplicate
                continue
            else:
                remaining_tasks.append(dep_task)

    updated_tasks.append(task)

    if not remaining_tasks:
        return updated_tasks
    else:
        return _recurse_dependencies(args, remaining_tasks[0], remaining_tasks[1:] if len(remaining_tasks) > 1 else [], updated_tasks)

def _update_build_tasks_based_on_dependencies(args, build_tasks):
    """
    Update the list of build_tasks and return it, based on required builds for fulfilling
    needed dependencies.
    """
    logging.info("Scanning dependencies...")
    updated_task_list = _recurse_dependencies(args, build_tasks[0], build_tasks[1:] if len(build_tasks) > 1 else [], [])
    logging.info(f"Updated task list: {updated_task_list}")
    return updated_task_list

def _build_given(args, build_tasks):
    """
    Builds the given list of tasks by first scanning for dependencies and adding to the task list
    based on the results.

    Returns the BuildResults list.
    """
    build_tasks = _update_build_tasks_based_on_dependencies(args, build_tasks)
    results, build_tasks_we_ran = _build_all_multiprocess(args, build_tasks)

    if None in results:
        logging.warning("At least one build process returned None instead of a BuildResult object. This is a programmer error.")
        results = [r for r in results if r is not None]

    return results, build_tasks_we_ran

def _build_all(args):
    """
    Build all the artifacts (note that this typically does not include the Yocto images).
    """
    if args.include_yocto:
        build_tasks = [t for t in BUILD_TASKS]
    else:
        build_tasks = [t for t in BUILD_TASKS if not t.name.startswith("yocto-")]
    return _build_given(args, build_tasks)

def _build_class_of_items(args):
    """
    Choose between the different categories and run one.
    """
    match args.module:
        case "all":
            return _build_all(args)
        case "all-fw":
            return _build_given(args, [t for t in BUILD_TASKS if t.name.startswith("fw-")])
        case "all-containers":
            return _build_given(args, [t for t in BUILD_TASKS if t.name.startswith("container-")])
        case "all-yocto":
            return _build_given(args, [t for t in BUILD_TASKS if t.name.startswith("yocto-")])
        case _:
            raise ValueError(f"{args.module} is invalid for some reason")

def build(args):
    """
    Top-level build function.
    """
    # Potentially clean first
    if args.clean:
        common.clean()

    if args.module.startswith("all"):
        # If all*, build a class of items
        results, build_tasks = _build_class_of_items(args)
    else:
        build_task = _find_task_from_name(args.module)
        assert build_task is not None, f"Somehow build_task is None (args.module: {args.module})"
        results, build_tasks = _build_given(args, [build_task])

    # Clean up after ourselves
    for task in build_tasks:
        task.clean_function(args)

    # Print the results for human consumption
    if isinstance(results, Iterable):
        results = sorted(results, key=lambda r: r.name)
        for result in results:
            print(result)
    else:
        print(results)

def fill_subparser(parser_build: argparse.ArgumentParser):
    parser_build.add_argument("module", choices=BUILD_CHOICES, help="The item to build")
    parser_build.add_argument("--artifact-folder", "-o", default=common.default_build_location())
    parser_build.add_argument("--clean", action='store_true', help="If given, we will run a 'clean' action first, then build.")
    parser_build.add_argument("--controller-module-yocto-image", default="artie-image-release", choices=["artie-image-dev", "artie-image-release"], type=str, help="The Yocto image to build for Controller Module.")
    parser_build.add_argument("--docker-repo", default=None, type=str, help="Docker repository.")
    parser_build.add_argument("--docker-tag", default=None, type=str, help="We apply this tag to each Docker image we build. If not given, we use the git hash.")
    parser_build.add_argument("--driver-base-image-tag", default=None, type=str, help="If building drivers, this is the tag that we use for the base images. If not given, we default to the git hash, or the artifact we build as part of this process if we are building all.")
    parser_build.add_argument("--enable-error-tracing", action='store_true', help="If given, error messages will include stack traces when possible.")
    parser_build.add_argument("--include-yocto", action='store_true', help="When building with 'all', we typically exclude Yocto images. Use this flag if you want to include them in 'all'.")
    parser_build.add_argument("--nprocs", default=multiprocessing.cpu_count(), type=int, help="If given, we will use at most this many processes to parallelize the build task. Note that this parallelization occurs at the artifact level, so we do not parellelize if you want to build a single item.")
    parser_build.set_defaults(cmd=build)
