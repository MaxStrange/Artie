"""
Module for common functions having to do with datasets
for language stuff.
"""
import experiments.configurations.configuration as configuration
import tensorflow as tf


def read_audio_files(pattern: str) -> tf.data.Dataset:
    """
    Creates a TF Dataset from reading in audio files from the given directory, recursively
    and decoding them from .wav format.

    Arguments
    ---------

    - pattern:  A shell glob-syntax pattern used to collect all the audio files. Each file should be a .wav file.

    """
    dataset = tf.data.Dataset.list_files(pattern)
    dataset = dataset.map(lambda fpath: tf.audio.decode_wav(fpath), num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset

def run_config_pipeline(wavs: tf.data.Dataset, config: configuration.Configuration) -> tf.data.Dataset:
    """
    Transforms the given input dataset, which should be a Dataset of wavs, into a Dataset
    where all the configuration's PREPROCESS_SIGNAL section's functions have been
    applied.
    """
    # Grab the functions, args, and kwargs
    functions = config.getimportablelist('PREPROCESS_SIGNAL', 'functions', none_okay=True)
    args = config.getlist('PREPROCESS_SIGNAL', 'args', none_okay=True)
    kwargs = config.getlist('PREPROCESS_SIGNAL', 'kwargs', none_okay=True)
    if not functions:
        # No functions to apply
        return wavs

    # Pad the args list to the same length as function list
    if args is None:
        args = [[] for _ in functions]
    elif len(args) > len(functions):
        raise configuration.ConfigError("'PREPROCESS_SIGNAL:args' has more values than 'PREPROCESS_SIGNAL:functions'")
    else:
        args.extend([[] for _ in functions])

    # Pad the kwargs list to the same length as function list
    if kwargs is None:
        kwargs = [{} for _ in functions]
    elif len(kwargs) > len(functions):
        raise configuration.ConfigError("'PREPROCESS_SIGNAL:kwargs' has more values than 'PREPROCESS_SIGNAL:functions'")
    else:
        kwargs.extend([{} for _ in functions])

    # Apply each function with its corresponding args and kwargs from the configuration file
    dataset = wavs
    for fn, args, kwargs in zip(functions, args, kwargs):
        dataset = fn(dataset, args, kwargs)

    return dataset

def transform_to_spectrograms(wavs: tf.data.Dataset, config: configuration.Configuration) -> tf.data.Dataset:
    """
    Transforms the given input dataset, which should be a Dataset of wavs, into a Dataset of spectrograms.
    """
    raise NotImplementedError()
