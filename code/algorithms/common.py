from typing import Dict, Any, Tuple, List
from collections.abc import Callable
import numpy as np
from numpy.typing import NDArray
import pyfar as pf
from matplotlib.axes import Axes

AudioRegion = NDArray[np.float64] # shape (channel, time)
AudioChunks = NDArray[np.float64] # shape (channel, chunk, time)
TFRegion = NDArray[np.complex128] # shape (channels, time, frequency)
MagnitudeSpectrogram = NDArray[np.float64] # shape (channels, time, frequency)
PanningHistogram = NDArray[np.float64] # shape (azimuth)


def polar_to_cartesian(r, phi):
    x = r * np.cos(phi)
    y = r * np.sin(phi)
    return x, y


def cartesian_to_polar(x, y):
    r = np.sqrt(x**2 + y**2)
    phi = np.arctan2(x, y)
    return r, phi


def chunked(audio: pf.Signal | AudioRegion, chunk_size: int, hop_size: int) -> AudioChunks:
    if isinstance(audio, pf.Signal):
        audio = audio.time
    # numpy black magic :)
    return np.lib.stride_tricks.sliding_window_view(audio, chunk_size, axis=-1)[..., ::hop_size, :]


def map_signal(sig: pf.Signal, func: Callable[[NDArray[np.float64]], NDArray[np.float64]]) -> pf.Signal:
    out = sig.copy()
    out.time = func(out.time)
    return out


def make_spectrogram(sig: pf.Signal, fft_size: int = 1024, hop_size: int = 512) -> TFRegion:
    return np.fft.rfft(chunked(sig, fft_size, hop_size))


def split_spectrogram_bands(
    spect: TFRegion,
    bands: NDArray[np.float64], # shape (band, (low,high))
    fft_size: int,
    sample_rate: float,
) -> List[TFRegion]:
    freqs = np.fft.rfftfreq(fft_size, d=1/sample_rate)
    regions = []
    for low, high in bands:
        mask = (freqs >= low) & (freqs <= high)
        regions.append(spect[..., mask])
    return regions


def draw_panning_histogram(
    hist: PanningHistogram,
    ax: Axes,
    title: str,
    ylim: Tuple[float, float],
    **plot_kwargs: Dict[Any, Any], 
):
    ax.plot(hist, **plot_kwargs)
    ax.set_yticks([])
    ax.set_title(title)
    ax.set_ylim(ylim)
    l = 0
    r = hist.shape[0] - 1
    c = r / 2
    ax.set_xticks([l,c,r], labels=['L', 'C', 'R'])
    ax.set_xlabel("Azimuth")
    ax.set_ylabel("Normalized histogram value")
    ax.legend(loc='upper left')
