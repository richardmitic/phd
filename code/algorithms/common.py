from collections.abc import Callable
import numpy as np
from numpy.typing import NDArray
import pyfar as pf

AudioRegion = NDArray[np.float64] # shape (channel, time)
AudioChunks = NDArray[np.float64] # shape (channel, chunk, time)
TFRegion = NDArray[np.complex128] # shape (channels, time, frequency)
MagnitudeSpectrogram = NDArray[np.float64] # shape (channels, time, frequency)

def chunked(audio: pf.Signal | AudioRegion, chunk_size: int, hop_size: int) -> AudioChunks:
    if isinstance(audio, pf.Signal):
        audio = audio.time
    # numpy black magic :)
    return np.lib.stride_tricks.sliding_window_view(audio, chunk_size, axis=-1)[..., ::hop_size, :]


def map_signal(sig: pf.Signal, func: Callable[[pf.Signal], pf.Signal]) -> pf.Signal:
    out = sig.copy()
    out.time = func(func.time)
    return out