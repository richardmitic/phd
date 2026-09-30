from typing import Tuple
import pyfar as pf
import numpy as np
from numpy.typing import NDArray
from pyfar.dsp.filter import GammatoneBands
import librosa
from algorithms.common import rms


def frequency_intensity_profile(
    sig: pf.Signal,
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    frequency_range = [20, 10000]
    resolution = 2
    gtb = GammatoneBands(
        frequency_range, resolution=resolution, sampling_rate=sig.sampling_rate
    )
    real, _ = gtb.process(sig)
    levels = rms(real.time, axis=(1, 2))
    levels_db = librosa.amplitude_to_db(levels, ref=np.max)
    freqs = pf.dsp.filter.erb_frequencies(frequency_range, resolution=resolution)
    return freqs, levels_db
