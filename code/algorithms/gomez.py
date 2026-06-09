import numpy as np
from numpy.typing import NDArray, ArrayLike

TFRegion = NDArray[np.complex128] # shape (channels, time, frequency)
SPSRegion = NDArray[np.complex128] # shape (time, frequency)
HistogramRegion = NDArray[np.float64] # shape (azimuth, time)
Histogram = NDArray[np.float64] # shape (azimuth)

def panning_spectrum(S: TFRegion) -> SPSRegion:
    Sl, Sr = S[0], S[1]
    return (2 / np.pi) * np.arctan(np.abs(Sl / Sr))

def perceptual_warp(x: ArrayLike) -> ArrayLike:
    return np.piecewise(
        x,
        [
            x >= 0.5,
            x < 0.5
        ],
        [
            lambda x: -0.5 + (2.5*x) - (x**2),
            lambda x: 1 - (-0.5 + (2.5*(1-x)) - (1-x)**2),
        ])

def energy_weighted_histogram(Rw: SPSRegion, S: TFRegion, M: int) -> HistogramRegion:
    i = np.floor(M * Rw).astype(int)
    amp = np.abs(np.sum(S, axis=0))
    out = []
    for t in np.arange(amp.shape[0]):
        hist = [np.sum(amp[t, i[t] == ik]) for ik in np.arange(M)]
        out.append(hist)
    return np.stack(out)

def panning_histogram(S: TFRegion, M: int) -> Histogram:
    R = panning_spectrum(S)
    Rw = perceptual_warp(R)
    hists = energy_weighted_histogram(Rw, S, M)
    Hw = np.mean(hists, axis=0)
    norm = np.sum(Hw)
    return Hw / norm

    