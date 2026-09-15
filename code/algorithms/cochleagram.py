import pyfar as pf
from python_auditory_toolbox import auditory_toolbox as pat
import numpy as np
import scipy
import librosa
from numpy.typing import NDArray
from typing import Tuple

from algorithms.common import MagnitudeSpectrogram

def cochleagram(
    audio: pf.Signal, 
    num_bands: int,
    chunk_length: float,
    hop_length: float,
) -> Tuple[NDArray[np.float64], MagnitudeSpectrogram]:
    sr = audio.sampling_rate

    erb_freqs = pat.ErbSpace(low_freq=100, high_freq=sr / 2, n=num_bands)[::-1]

    coefs = pat.MakeErbFilters(sr, num_bands, low_freq=100)
    y = pat.ErbFilterBank(audio.time[0], coefs)
    y *= np.sign(y)  # half wave rectify
    y = np.sqrt(y)  # square root

    # low pass
    fc = 800
    b, a = scipy.signal.butter(4, fc / sr, btype="low", analog=False)
    y = scipy.signal.filtfilt(b, a, y)

    chunk_size = int(chunk_length * sr)
    hop_size = int(hop_length * sr)
    chunks = np.lib.stride_tricks.sliding_window_view(y, chunk_size, axis=1)[
        :, ::hop_size, :
    ]
    coch = librosa.amplitude_to_db(np.mean(chunks, axis=2))
    return erb_freqs, coch