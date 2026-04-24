import numpy as np
from numpy.typing import NDArray

TFRegion = NDArray[np.complex128] # shape (channels, time, frequency)

def expectation(x: NDArray) -> NDArray:
    return x

def cross_correlation(Xi: TFRegion, Xj: TFRegion, lamb: float) -> TFRegion:
    sigma_ij = np.zeros_like(Xi)

    # Note: when m==0, m-1 will take the final time slice. It shouldn't
    # really do that mathematically, but it will be zeros anyway. 
    for m in np.arange(sigma_ij.shape[0]):
        sigma_ij[m] = ((1-lamb) * sigma_ij[m-1]) + (lamb * Xi[m] * Xj[m])
    
    return sigma_ij

def ambiance_index(X: TFRegion, lamb: float = 0.1) -> TFRegion:
    sigma_12 = cross_correlation(X[0], X[1], lamb)
    sigma_11 = cross_correlation(X[0], X[0], lamb)
    sigma_22 = cross_correlation(X[1], X[1], lamb)
    sigma = np.abs(sigma_12) / np.pow((sigma_11 * sigma_22), 0.5)
    return 1 - sigma

def panning_index(X: TFRegion) -> TFRegion:
    psi_12 = cross_correlation(X[0], X[1], 1.)
    psi_11 = cross_correlation(X[0], X[0], 1.)
    psi_22 = cross_correlation(X[1], X[1], 1.)
    psi = 2 * np.abs(psi_12) / (psi_11 + psi_22)
    psi_1 = np.abs(psi_12) / psi_11
    psi_2 = np.abs(psi_12) / psi_12
    delta_hat = np.sign(psi_1 - psi_2)
    return (1 - psi) * delta_hat