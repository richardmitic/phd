import numpy as np
from numpy.typing import NDArray, ArrayLike

from .common import TFRegion

SPSRegion = NDArray[np.complex128] # shape (time, frequency)
HistogramRegion = NDArray[np.float64] # shape (azimuth, time)
Histogram = NDArray[np.float64] # shape (azimuth)

def panning_spectrum(S: TFRegion) -> SPSRegion:
    Sl, Sr = S[0], S[1]
    return (2 / np.pi) * np.arctan(np.abs(Sr / Sl))

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

def panning_histogram(S: TFRegion, M: int = 100) -> Histogram:
    R = panning_spectrum(S)
    Rw = perceptual_warp(R)
    hists = energy_weighted_histogram(Rw, S, M)
    Hw = np.mean(hists, axis=0)
    norm = np.sum(Hw)
    return Hw / norm

def panning_coefficients(ph: Histogram, L: int = 20) -> NDArray[np.float64]:
    pseudospect = np.concat([ph, ph[::-1]])
    return np.fft.ifft(np.log(pseudospect))[:L]

def cepstral_quantize(ph: Histogram, L: int = 20) -> Histogram:
    M = len(ph)
    pc = panning_coefficients(ph, L)
    x = np.concat([pc, np.zeros(2*M-L)])
    x = np.exp(np.fft.fft(x).real)
    x = x[:len(x) // 2]
    x = x / np.sum(x)
    return x