from numpy.typing import NDArray
from algorithms import sarroff, gomez
from .common import make_spectrogram, split_spectrogram_bands, TFRegion
import pyfar as pf
import numpy as np
from functools import partial


def __sarroff_ph_tfregion(X: TFRegion, **kwargs) -> NDArray[np.float64]:
    "Helper function to run sarroff PH on complex spectrogram data"
    return sarroff.panning_histogram(np.abs(X), **kwargs)

def sip(
    audio: pf.Signal,
    fft_size: int,
    hop_size: int,
    n_azimuth_bins: int,
    subbands: NDArray[np.float64], # shape (band, (low, high))
    algorithm: str = 'gomez'
) -> NDArray[np.float64]:
    spect = make_spectrogram(audio, fft_size=fft_size, hop_size=hop_size)
    sub_spects = split_spectrogram_bands(spect, subbands, fft_size, audio.sampling_rate)
    if algorithm == 'gomez':
        ph_func = partial(gomez.panning_histogram, M = n_azimuth_bins)
    elif algorithm == 'sarroff':
        ph_func = partial(__sarroff_ph_tfregion, beta = n_azimuth_bins // 2)
    else:
        raise Exception(f"{algorithm} is not a panning histogram method")
    hists = np.array([ph_func(s) for s in sub_spects])
    hists = hists / np.atleast_2d(np.max(hists, axis=1)).T # normalize
    return hists