from typing import List, Optional
from collections.abc import Callable
import numpy as np
from numpy.typing import NDArray
import pyfar as pf
from matplotlib.axes import Axes
from pathlib import Path
import soundfile

AudioRegion = NDArray[np.float64]  # shape (channel, time)
AudioChunks = NDArray[np.float64]  # shape (channel, chunk, time)
TFRegion = NDArray[np.complex128]  # shape (channels, time, frequency)
MagnitudeSpectrogram = NDArray[np.float64]  # shape (channels, time, frequency)
PanningHistogram = NDArray[np.float64]  # shape (azimuth)


def read_audio(
    file: Path, start: float = 0.0, duration: Optional[float] = None
) -> pf.Signal:
    sfinfo = soundfile.info(file)
    sr = sfinfo.samplerate
    start_sample = int(start * sr)
    duration_samples = -1 if duration is None else int(duration * sr)
    return pf.io.read_audio(file, start=start_sample, frames=duration_samples)


def rms(arr: NDArray[np.floating], axis=None) -> float:
    return np.sqrt(np.sum(arr**2, axis=axis))


def polar_to_cartesian(r, phi):
    x = r * np.cos(phi)
    y = r * np.sin(phi)
    return x, y


def cartesian_to_polar(x, y):
    r = np.sqrt(x**2 + y**2)
    phi = np.arctan2(x, y)
    return r, phi


def chunked(
    audio: pf.Signal | AudioRegion, chunk_size: int, hop_size: int
) -> AudioChunks:
    if isinstance(audio, pf.Signal):
        audio = audio.time
    # numpy black magic :)
    return np.lib.stride_tricks.sliding_window_view(audio, chunk_size, axis=-1)[
        ..., ::hop_size, :
    ]


def map_signal(
    sig: pf.Signal, func: Callable[[NDArray[np.float64]], NDArray[np.float64]]
) -> pf.Signal:
    out = sig.copy()
    out.time = func(out.time)
    return out


def make_spectrogram(
    sig: pf.Signal, fft_size: int = 1024, hop_size: int = 512
) -> TFRegion:
    return np.fft.rfft(chunked(sig, fft_size, hop_size))


def split_spectrogram_bands(
    spect: TFRegion,
    bands: NDArray[np.float64],  # shape (band, (low,high))
    fft_size: int,
    sample_rate: float,
) -> List[TFRegion]:
    freqs = np.fft.rfftfreq(fft_size, d=1 / sample_rate)
    regions = []
    for low, high in bands:
        mask = (freqs >= low) & (freqs <= high)
        regions.append(spect[..., mask])
    return regions


def downmix_to_mono(sig: pf.Signal) -> pf.Signal:
    a = 1 / np.sqrt(2)
    return pf.Signal(
        (sig.time[0] * a) + (sig.time[1] * a), sampling_rate=sig.sampling_rate
    )


def upmix_to_stereo(sig: pf.Signal) -> pf.Signal:
    a = 1 / np.sqrt(2)
    return pf.Signal(
        np.stack([sig.time[0], sig.time[0]]) * a, sampling_rate=sig.sampling_rate
    )


def peak_normalize(sig: pf.Signal) -> pf.Signal:
    amp = np.max(np.abs(sig.time))
    return sig / amp