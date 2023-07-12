"""
This module contains the actual machinery for running tasks.
"""
from . import artifact
from . import result
from . import task
from .. import common
from typing import List
import logging
import multiprocessing
import traceback

class TaskWrapper:
    def __init__(self, func, q: multiprocessing.Queue, worker_index: int):
        self._func = func
        self._q = q
        self._worker_index = worker_index

    def __call__(self, args):
        common.set_up_logging(args)
        try:
            res = self._func(args)
        except Exception as e:
            name = multiprocessing.current_process().name
            res = result.ErrorTaskResult(name=name, error=e)
            if args.enable_error_tracing:
                logging.error(f"Error running task {name}: {''.join(traceback.format_exception(e))}")
        logging.info("Putting result onto queue")
        try:
            # If we freeze here, it is likely because the result object can't be pickled
            self._q.put((self._worker_index, res))
        except AttributeError as e:
            logging.error(f"Cannot pickle the result object: {e}")
            while True:
                pass

def _task_has_already_been_run(task_name: str, tasks_we_have_run_so_far) -> bool:
    """
    Returns whether the task with `task_name` is found in `tasks_we_have_run_so_far`.
    """
    for t in tasks_we_have_run_so_far:
        if task_name == t.name:
            return True
    return False

def _check_if_task_is_ready(args, t: task.Task, tasks_we_have_run_so_far):
    """
    Check if the given task `t` is ready to run.
    """
    # If this task has no dependencies, it is ready to go
    if not t.dependencies:
        logging.info(f"Found a ready task: {t.name}")
        return True

    # Otherwise, we have to check each of this task's dependencies
    # to see if they have been run
    for dep in t.dependencies:
        depname = dep.producing_task_name
        artifact_name = dep.artifact_name

        # If we are depending on an artifact, check if it is built
        if artifact_name and artifact.is_built(args, depname, artifact_name):
            # If it is, move onto the next dependency
            continue

        # If it isn't, or if we only depend on the task, not an artifact,
        # check if depname has run already.
        if not _task_has_already_been_run(depname, tasks_we_have_run_so_far):
            # If the dependency has not run, we are waiting for it to run. We can't run this task yet.
            return False

        # We couldn't find `artifact_name` in the built artifacts, but `depname` has already run.
        # This is probably an error state, but to prevent hanging, let's ignore this and warn the user.
        logging.warning(f"Task {t.name} depends on {depname}'s {artifact_name} artifact, but even though {depname} has run, {artifact_name} is not marked as built.")
    return True

def _check_tasks_against_dependencies(args, tasks, tasks_we_have_run_so_far):
    """
    Check each task against args._artifacts to see
    if anything is ready to run. If so, return the index of it.
    If nothing is found, return None.
    """
    for i, t in enumerate(tasks):
        if _check_if_task_is_ready(args, t, tasks_we_have_run_so_far):
            return i

    # Couldn't find one
    return None

def _run_all_multiprocess(args, tasks):
    """
    Run the given `tasks`, each with `args` in parallel, using however many
    maximum processes have been specified in `args` (which may be 1).
    """
    ntasks = len(tasks)
    results = []
    workers = [None for _ in range(min(args.nprocs, ntasks))]
    q = multiprocessing.Queue()
    tasks_we_ran = []
    while len(results) != ntasks:
        have_capacity = None in workers
        still_work_to_do = len(tasks) > 0

        if have_capacity and still_work_to_do:
            task_ready_index = _check_tasks_against_dependencies(args, tasks, tasks_we_ran)
        else:
            task_ready_index = None

        if have_capacity and still_work_to_do and task_ready_index is not None:
            # Create a new worker to do some work
            worker_index = workers.index(None)
            task_to_do = tasks.pop(task_ready_index)
            p = multiprocessing.Process(target=TaskWrapper(task_to_do, q, worker_index), args=(args,), name=task_to_do.name, daemon=True)
            workers[worker_index] = (p, task_to_do)
            workers[worker_index][0].start()
        else:
            # Otherwise, sleep until at least one worker is done
            # When that worker is done, collect its results and terminate the worker process
            worker_index, result = q.get()
            results.append(result)
            workers[worker_index][0].join()
            task_we_ran = workers[worker_index][1]
            tasks_we_ran.append(task_we_ran)
            workers[worker_index] = None
            # Append artifacts to args so that dependent tasks can access them
            artifact.add_artifacts_from_result(args, result)
            logging.info(f"Task {result.name} finished.")
    return results, tasks_we_ran

def _recurse_dependencies(args, t: task.Task, remaining_tasks: List[task.Task], updated_tasks: List[task.Task], all_tasks: List[task.Task]):
    if t.dependencies is not None:
        to_remove = []
        for dep in t.dependencies:
            name = dep.producing_task_name
            dep_task = common.find_task_from_name(name, all_tasks)
            if dep_task is None:
                logging.error(f"Attempted to find a task: {name}, but task not found in all_tasks. We'll remove this dependency and try to run the task, but it will likely fail. All tasks: {[tsk.name for tsk in all_tasks]}")
                to_remove.append(name)
            elif dep_task in remaining_tasks or dep_task in updated_tasks:
                # Duplicate
                continue
            else:
                remaining_tasks.append(dep_task)
        # If we encountered any errors, remove the offending dependency
        for d in to_remove:
            del t.dependencies[d]

    updated_tasks.append(t)

    if not remaining_tasks:
        return updated_tasks
    else:
        return _recurse_dependencies(args, remaining_tasks[0], remaining_tasks[1:] if len(remaining_tasks) > 1 else [], updated_tasks, all_tasks)

def _update_tasks_based_on_dependencies(args, tasks: List[task.Task], all_tasks: List[task.Task]):
    """
    Update the list of tasks and return it, based on required tasks for fulfilling
    needed dependencies.
    """
    logging.info("Scanning dependencies...")
    updated_task_list = _recurse_dependencies(args, tasks[0], tasks[1:] if len(tasks) > 1 else [], [], all_tasks)
    return updated_task_list

def _recurse_check_if_cached(args, t: task.Task, all_tasks: List[task.Task]) -> bool:
    if not isinstance(t, task.BuildTask):
        return False
    elif not t.cached(args):
        return False
    elif not t.dependencies:
        return True
    else:
        deptasks = [common.find_task_from_name(d.producing_task_name, all_tasks) for d in t.dependencies]
        return all([_recurse_check_if_cached(args, deptask, all_tasks) for deptask in deptasks])

def _remove_tasks_based_on_cache(args, tasks: List[task.Task], all_tasks: List[task.Task]):
    """
    Remove tasks if they are Build Tasks and if their
    artifacts have already been built AND all of their dependencies
    have also been built, unless --force-build is in `args`.
    """
    if args.force_build:
        logging.info("--force-build detected. Skipping cache checks.")
        return tasks
    else:
        logging.info("Removing tasks based on cache...")

    ret = []
    for t in tasks:
        if _recurse_check_if_cached(args, t, all_tasks):
            logging.info(f"Task {t.name} cached. No need to re-run. Use --force-build to override.")
            t.fill_args_with_artifacts(args)  # Make sure to add its artifacts to the args list for other tasks to consume
        else:
            ret.append(t)
    return ret

def _fill_artifacts(args, tasks: List[task.Task]):
    """
    Ask each task to fill each of its artifacts' values, though
    their build flags will still be False.
    """
    logging.info("Filling in artifact values based on CLI args...")
    for t in tasks:
        t.fill_artifacts_at_runtime(args)
    return tasks

def _mark_tasks_as_cached(args, tasks: List[task.Task]) -> List[task.Task]:
    """
    Ask each task to mark its artifacts as built if they are already built,
    unless --force-build has been passed.
    """
    if args.force_build:
        return tasks

    logging.info("Checking which tasks are cached...")
    for t in tasks:
        t.mark_if_cached(args)
    return tasks

def run_tasks(args, tasks: List[task.Task], all_tasks: List[task.Task]):
    """
    Runs the given list of tasks by first scanning for dependencies and adding to the task list
    based on the results.

    Returns the Results list and the actual tasks that were run (which may not match `tasks`, due to
    cached items and dependencies).
    """
    # Allow tasks to retrieve artifacts from other tasks
    artifact.initialize(args)

    # ask all tasks to fill their artifacts
    all_tasks = _fill_artifacts(args, all_tasks)

    # add dependency tasks
    tasks = _update_tasks_based_on_dependencies(args, tasks, all_tasks)

    # check each item for cached
    tasks = _mark_tasks_as_cached(args, tasks)

    # remove tasks if they are cached AND all of their dependencies are cached
    tasks = _remove_tasks_based_on_cache(args, tasks, all_tasks)

    if not tasks:
        logging.info("Nothing to do.")
    else:
        logging.info(f"Updated task list: {tasks}")

    results, tasks_we_ran = _run_all_multiprocess(args, tasks)

    if None in results:
        logging.error("At least one task returned None instead of a Result object. This is a programmer error.")
        results = [r for r in results if r is not None]

    return results, tasks_we_ran
