from enum import Enum
import numpy as np
import pyfar as pf
from numpy.typing import NDArray
from librosa import amplitude_to_db

from algorithms.common import make_spectrogram, split_spectrogram_bands, downmix_to_mono


class StereoWidth(Enum):
    MONO = 0
    NARROW = 1
    BALANCED = 2
    WIDE = 3


def _rms(x, axis=None):
    return np.sqrt(np.mean(x**2, axis=axis))


def stereo_width(sig: pf.Signal) -> float:
    if sig.cshape == (1,):
        return 0.0
    else:
        return float(np.mean(np.abs(sig.time[1] - sig.time[0])))


def stereo_width_category(sig: pf.Signal) -> StereoWidth:
    width = stereo_width(sig)
    if width < 0.001:
        return StereoWidth.MONO
    elif width < 0.05:
        return StereoWidth.NARROW
    elif width < 0.1:
        return StereoWidth.BALANCED
    else:
        return StereoWidth.WIDE


def mono_compatibility(sig: pf.Signal) -> float:
    if sig.cshape == (1,):
        return 1.0
    mid = sig.time[1] + sig.time[0]
    side = sig.time[1] - sig.time[0]
    return float(np.min(np.corrcoef(mid, side)))


def compression(sig: pf.Signal) -> float:
    if sig.cshape == (1,):
        mid = sig.time[0]
    else:
        mid = sig.time[0] + sig.time[1]
    return float(np.log10(np.max(mid) / _rms(mid)) * 20)


def averge_phase_difference(sig: pf.Signal) -> float:
    if sig.cshape == (1,):
        return 0.0
    else:
        return float(np.mean(np.abs(np.atan2(sig.time[1], sig.time[0]))))


def clipping(sig: pf.Signal) -> int:
    return int(np.count_nonzero(np.abs(sig.time) > 1))


def tonal_profile(sig: pf.Signal) -> NDArray[np.float64]:
    spect = make_spectrogram(downmix_to_mono(sig))

    def _energy(spect):
        return amplitude_to_db(np.mean(np.abs(spect)))

    bands = split_spectrogram_bands(
        spect,
        np.array([[20, 250], [250, 2000], [2000, 8000], [8000, 20000]]),
        1024,
        sig.sampling_rate,
    )
    fip = np.array([_energy(b) for b in bands]) - _energy(spect)

    return fip
