# Artie Tool Contribution Guide

This document provides guidelines and best practices for contributing changes
to Artie Tool.

## Overview of Artie Tool

For a good overview of Artie Tool, see [the Setting up your Development Environment Guide](./development-environment.md#working-with-artie-tool).

There are two types of updates you might do to Artie Tool:

1. Update the source code
1. Update the tasks

Updating the source code should not be necessary unless you are making
a new feature, fixing a bug, or increasing Artie Tool's performance.
If that is the case, see the section on [How Artie Tool Works](#how-artie-tool-works).

Updating or adding new tasks, on the other hand, is a frequent part of
normal development with Artie. To update Artie Tool to be able
to build something new, flash something new, test something new,
or deploy something new, you will need to create or update a task file.
See the appropriate section of [the Setting up your Development Environment Guide](./development-environment.md#working-with-artie-tool)
and the [Artie Tool Task Specification](../../framework/artietool/tasks/README.md) for understanding how to do this.

## How Artie Tool Works

Artie Tool is a Python CLI application that is responsible for all manner
of administrative tasks pertaining to the Artie project.

In detail, here is how it works:

1. Artie Tool calls `fill_subparser()` on each subcommand module.
   The subcommands are found in the `artietool` folder. The `fill_subparser()` function
   flls in any argparse arguments that subcommand may need
   and then, if the subcommand operates on tasks (such
   as build, flash, test, or deploy), it also fills in the
   possible tasks in argparse.
1. The `cmd` argument is run in whichever submodule was chosen.
1. Depending on what submodule is chosen, the `cmd` argument does different
   things, and for most of the submodules, this is easy to follow.
   For the more comlicated submodules (the ones that use tasks),
   the general flow continues with the next step.
1. Artie Tool determines which task or class of tasks is chosen by
   the user, then calls `run.run_tasks()` to run the tasks.
1. In order to run the appropriate tasks, the `run_tasks()` function
   does the following:
     1. Call `fill_artifacts_at_runtime()` on each task, passing in the
        runtime args. This in turn calls `fill_artifacts_at_runtime()`
        on each job in each task, which asks each of that job's artifacts
        to `fill_item()` based on the runtime args.
        This method ensures each artifact's `item` property is set.
        An artifact's `item` is the actual thing that artifact
        encapsulates: a Yocto binary image file, a Docker image name,
        etc. We typically have to wait until runtime to fill this item
        in completely because it may for example be a path relative
        to somewhere the user has selected, or its name may be something
        the user passes in as an argument.
    1. Next, check the target tasks for dependencies, then recursively
       check those tasks for dependencies, etc., until there is a
       list of tasks that must be run.
    1. Check each task in the list to see if each of its artifacts
       are already found on disk. Each task whose artifacts are all
       cached is removed from the list (but only if its
       dependencies are also removed from the list).
    1. At this point, if there are any tasks remaining, the
       tasks are executed. The execution is parallelized at the task
       level: a single task gets a single process (but only up to the
       maximum parallelization determined by user args and number of CPUs).
       Each task is only run once all of its (recursive) dependencies
       are run.

## Source Code

Artie Tool's source code lives in `framework/artietool`.

Each task type is a class and lives inside `framework/artietool/infrastructure/task.py`. Each type of job is
also a class and lives inside `framework/artietool/infrastructure/*_job.py`.
