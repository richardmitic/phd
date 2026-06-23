import numpy as np
from numpy.typing import NDArray

from algorithms.avendano import panning_index
from algorithms.common import TFRegion


def panning_rms(sps: NDArray[np.float64]) -> NDArray[np.float64]:
    num_bands = sps.shape[1]
    prms = np.sqrt((1 / num_bands)) * np.sum(sps**2, axis=1)
    return prms


def stereo_panning_features(spect: TFRegion,  samplerate: float, M: int):
    sps = panning_index(spect)

    freqs = np.fft.rfftfreq((sps.shape[1] - 1) * 2, d=1/samplerate)

    # Panning index can be NaN when the input audio is digital zero.
    # Mask away any whole time frames that contain NaNs
    nan_mask = np.any(np.isfinite(sps), axis=1) & ~np.any(np.isnan(sps), axis=1)
    sps = sps[nan_mask]
    
    low_mask = freqs <= 250
    mid_mask = (freqs >= 250) & (freqs <= 2500)
    high_mask = freqs >= 2500

    low_band = sps[:, low_mask]
    mid_band = sps[:, mid_mask]
    high_band = sps[:, high_mask]

    P_total = panning_rms(sps)
    P_low = panning_rms(low_band)
    P_mid = panning_rms(mid_band)
    P_high = panning_rms(high_band)

    P = np.stack([P_total, P_low, P_mid, P_high]).T
    windows = np.lib.stride_tricks.sliding_window_view(P, M, axis=0)

    m_phi = np.mean(windows, axis=2)
    s_phi = np.std(windows, axis=2)
    P_running = np.hstack([m_phi, s_phi])

    # final vector is:
    # 0  full | running mean | mean
    # 1  low  | running mean | mean
    # 2  mid  | running mean | mean
    # 3  high | running mean | mean
    # 4  full | running std  | mean
    # 5  low  | running std  | mean
    # 6  mid  | running std  | mean
    # 7  high | running std  | mean
    # 8  full | running mean | std
    # 9  low  | running mean | std
    # 10 mid  | running mean | std
    # 11 high | running mean | std
    # 12 full | running std  | std
    # 13 low  | running std  | std
    # 14 mid  | running std  | std
    # 15 high | running std  | std
    feature_vector = np.hstack([np.mean(P_running, axis=0), np.std(P_running, axis=0)])

    # "running mean" can be seen as "long term panning"
    # "running std" can be seen as "short term panning"

    return feature_vector

