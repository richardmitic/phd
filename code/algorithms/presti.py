from algorithms.common import TFRegion
import numpy as np
from numpy.typing import NDArray

def azimuth(spect: TFRegion) -> NDArray[np.float64]:
    mid, side = spect[1] + spect[0], spect[1] - spect[0]
    mid_mag, side_mag = np.abs(mid), np.abs(side)
    ms_phase_diff = np.angle(mid) - np.angle(side)
    pan = 0.5 * np.atan2(
        2 * side_mag * mid_mag * np.cos(ms_phase_diff),
        mid_mag**2 - side_mag**2
    )

    return pan

def clarity(spect: TFRegion) -> NDArray[np.float64]:
    L, R = spect
    lr_phase_diff = np.angle(R) - np.angle(L)
    return 0.5 * (np.cos(2 * lr_phase_diff) + 1)