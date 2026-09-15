import numpy as np
from collections import namedtuple
from numpy.typing import NDArray
from typing import NamedTuple

FrequencyAzimuthPlane = NDArray[np.float64] # shape (frequency, azimuth)
FrequencyAzimuthAnalysisSignal = NDArray[np.float64] # shape (time, frequency, azimuth)

"Type for the magnitude spectrum of a single time slice"
MagnitudeSpectrum = NDArray[np.float64] # shape (channel, frequency)

from .common import MagnitudeSpectrogram, TFRegion  # shape (channel, time, frequency)


def frequency_azimuth_plane_slow(X: MagnitudeSpectrum, beta: int) -> FrequencyAzimuthPlane:
    """
    Calculate the frequency-azimuth plane for a stereo magnitude spectrogram.
    This version is slow, but follows the paper exactly.
    """
    g = np.arange(beta + 1) / beta
    num_bins = X.shape[-1]

    Azl = np.zeros((num_bins, beta + 1))
    Azr = np.zeros((num_bins, beta + 1))
    for i in np.arange(beta + 1):
        for k in np.arange(num_bins):
            Azr[k, i] = np.abs(X[0,k] - g[i] * X[1,k])
            Azl[k, i] = np.abs(X[1,k] - g[i] * X[0,k])
    
    Az = np.hstack([Azl, np.fliplr(Azr[:, :-1])])
    Az = convert_nulls_to_peaks(Az)
    
    return Az

def frequency_azimuth_plane(X: MagnitudeSpectrum, beta: int, inverted=True) -> FrequencyAzimuthPlane:
    """
    Calculate the frequency-azimuth plane for a stereo magnitude spectrogram.
    This version is much faster since it uses numpy's vectorized functions, 
    but it's harder to read.
    """
    Xl, Xr = X[0], X[1]
    g = np.arange(beta + 1) / beta
    num_bins = X.shape[-1]

    k, i = np.dstack(np.mgrid[:num_bins, : beta + 1]).reshape(-1, 2).T

    Azl = np.abs(Xr[k] - g[i] * Xl[k]).reshape((num_bins, beta + 1))
    Azr = np.abs(Xl[k] - g[i] * Xr[k]).reshape((num_bins, beta + 1))

    Az = np.hstack([Azl, np.fliplr(Azr[:, :-1])])
    if inverted:
        Az = convert_nulls_to_peaks(Az)

    return Az


def convert_nulls_to_peaks(Az: NDArray[np.float64]) -> NDArray[np.float64]:
    az_peaks = np.max(Az, axis=1) - np.min(Az, axis=1)
    az_argmin = np.argmin(Az, axis=1)
    k = np.arange(Az.shape[0])
    Az_inv = np.zeros_like(Az)
    Az_inv[k, az_argmin] = az_peaks
    return Az_inv


def frequency_azimuth_analysis_signal(X: MagnitudeSpectrogram, beta: int, inverted=True) -> FrequencyAzimuthAnalysisSignal:
    planes = []
    for m in np.arange(X.shape[1]):
        # print(m)
        Az = frequency_azimuth_plane(X[:, m, :], beta, inverted=inverted)
        planes.append(Az)
    
    return np.stack(planes)


def panning_histogram(X: MagnitudeSpectrogram, beta: int = 20) -> NDArray[np.float64]:
    analysis_signal = frequency_azimuth_analysis_signal(X, beta)
    hist = analysis_signal.sum(axis=(0,1)) # sum over time and frequency
    # hists = analysis_signal.sum(axis=1)
    return hist

def panning_histogram_region(X: MagnitudeSpectrogram, beta: int = 20) -> NDArray[np.float64]:
    analysis_signal = frequency_azimuth_analysis_signal(X, beta=beta)
    return analysis_signal.sum(axis=1) # sum over frequency


def stereo_width_stats(ph: NDArray[np.float64]) -> NamedTuple:
    bin_midpoints = np.linspace(-1, 1, len(ph))
    mean = np.sum(ph * bin_midpoints)
    stddev = np.sqrt(np.sum(ph * (bin_midpoints - mean) ** 2))
    full_width_half_maximum = 2 * np.sqrt(2 & np.log(2)) * stddev
    return namedtuple("StereoWidthStats", ["mean", "std", "fwhm"], mean, stddev, full_width_half_maximum)
