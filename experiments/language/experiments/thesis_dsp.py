"""
Full thesis experiment, with DSP stuff to make it totally back-propable.
"""
import experiments.configurations.configuration as myconf
import experiments.language.datasets as datasets
import tensorflow as tf


def run(config: myconf.Configuration, savedir: str):
    """
    Summary
    -------

    This experiment is a port of my thesis to the new and improved Artie framework.
    The gist of it is the following:

    1. Artie retrieves sounds from a directory of saved audio files, preprocesses them into cleanish
       speech in English or Chinese, and converts them into the frequency domain via spectrogramification.
    2. An autoencoder is trained to take in these spectrograms and output them, thereby learning an embedding space.
    3. Artie selects some sounds to try to mimic by using differentiable DSP stuff to synthesize sounds. These sounds
       are then fed into the encoder to land them in the embedding space, and the distance between the result
       and the target in the embedding space is used as the loss function (we try to minimize this distance)
       in backpropagation.
    4. We train on these few sounds until we converge and we save a bunch of stuff to analyze along the way.

    Arguments
    ---------

    - config:   The configuration object for this experiment
    - savedir:  The path to the directory where we will save results

    """
    # Read the sound files into a TF dataset that preprocesses them into spectrograms
    # Create the autoencoder from the config file specifications
    # Train the autoencoder (unless already trained)
    # Create the DDSP synthesizer network from the config file specifications
    # Pretrain the synthesizer network to make babbling noises (maybe)
    # Create the super network (Sample from embedding space -> DDSP Synthesizer network -> encoding layers -> embedding loss function)
    # Train the super network
    pass
