import numpy as np
from numpy.typing import NDArray
import pyfar as pf
from scipy.signal import hilbert, butter, filtfilt

from python_auditory_toolbox import auditory_toolbox as pat

from .common import chunked

Cochleagram = NDArray[np.float64] # shape (channel, time, frequency)


def modulate_envelope(x: NDArray[np.float64]) -> NDArray[np.float64]:
    envelope = np.power(np.abs(hilbert(x)), 0.23)
    return x * envelope

def cochleagram(audio: pf.Signal, chunk_time: float, hop_time: float, num_bands: int) -> Cochleagram:
    coefs = pat.MakeErbFilters(audio.sampling_rate, num_bands, low_freq=100)

    y = np.stack([pat.ErbFilterBank(chan, coefs) for chan in audio.time])
    print(y.shape)
    y = modulate_envelope(y)
    print(y.shape)
    y *= np.sign(y) # half wave rectify
    print(y.shape)
    y = np.sqrt(y) # square root
    print(y.shape)
    
    # lowpass
    fc = 800
    b, a = butter(4, fc/audio.sampling_rate, btype='low', analog=False)
    y = filtfilt(b, a, y)
    print(y.shape)
    
    chunk_size = int(chunk_time * audio.sampling_rate)
    hop_size = int(hop_time * audio.sampling_rate)
    chunks = np.stack([chunked(chan, chunk_size, hop_size) for chan in y]) # shape (channel, freq_band, chunk, sample)
    cochleagram = chunks.mean(axis=-1)
    print(cochleagram.shape)

    return cochleagram
