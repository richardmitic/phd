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

def extract_envelope(x: NDArray[np.float64], sampling_rate: float) -> NDArray[np.float64]:
    x = modulate_envelope(x)
    x *= np.sign(x) # half wave rectify
    x = np.sqrt(x) # square root
    
    # lowpass
    fc = 800
    b, a = butter(4, fc/sampling_rate, btype='low', analog=False)
    return filtfilt(b, a, x)

def make_subbands(audio: pf.Signal, num_bands: int) -> NDArray[np.float64]:
    coefs = pat.MakeErbFilters(audio.sampling_rate, num_bands, low_freq=100)
    return np.stack([pat.ErbFilterBank(chan, coefs) for chan in audio.time])


def make_cochleagram(envelope:NDArray[np.float64], chunk_size: int, hop_size: int) -> NDArray[np.float64]:
    chunks = np.stack([chunked(chan, chunk_size, hop_size) for chan in envelope]) # shape (channel, freq_band, chunk, sample)
    cochleagram = chunks.mean(axis=-1)
    return cochleagram


def cochleagram(audio: pf.Signal, chunk_time: float, hop_time: float, num_bands: int) -> Cochleagram:
    x = make_subbands(audio, num_bands)
    envelope = extract_envelope(x)
    
    chunk_size = int(chunk_time * audio.sampling_rate)
    hop_size = int(hop_time * audio.sampling_rate)
    return make_cochleagram(envelope, chunk_size, hop_size)
