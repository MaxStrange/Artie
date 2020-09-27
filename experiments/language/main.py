"""
Run this file like this:

`python -m experiments.language.main <args>`

from the root of this repository.

This is the main.py file for experimenting with language using the Artie platform.
Use an experiments/configurations config file with this application.
"""
import argparse
import experiments.configurations.configuration as myconf
import logging
import numpy as np
import os
import random
import software.utils as softwareutils
import tensorflow as tf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=lambda arg: softwareutils.validate_fpath(parser, arg), help="Path to a valid configuration file.")
    parser.add_argument("--loglevel", choices=["debug", "info", "warning", "error", "critical"], default="info", help="Log level for logging during the experiment.")
    parser.add_argument("--logfile-name", type=str, default="logfile.log", help="Name of the logfile to write logs to. We create a file of this name inside the experiment's results directory.")
    args = parser.parse_args()

    # Load the correct config file
    config = myconf.load(args.config)

    # Make a folder for the analysis results
    experimentname = config.getstr('EXPERIMENT', 'name')
    saveroot = config.getpath('EXPERIMENT', 'save-root')
    savedir = os.path.join(saveroot, experimentname)
    os.makedirs(savedir, exist_ok=True)

    # Set up the logging configuration
    loglevel = getattr(logging, args.loglevel.upper())
    logging.basicConfig(filename=os.path.join(savedir, args.logfile_name), filemode='w', level=loglevel)

    # Random seed
    randomseed = config.getint('EXPERIMENT', 'random-seed')
    np.random.seed(randomseed)
    random.seed(randomseed)
    tf.random.set_seed(randomseed)
    # Note that due to using a GPU and using multiprocessing, reproducibility is not guaranteed
    # But the above lines do their best

    # Set up and run the experiment
    experiment_function = config.getimportable('EXPERIMENT', 'function')
    experiment_function(config, savedir)
