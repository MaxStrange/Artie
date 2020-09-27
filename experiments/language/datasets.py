"""
Module for common functions having to do with datasets
for language stuff.
"""
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
