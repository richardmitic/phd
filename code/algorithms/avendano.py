import numpy as np
from numpy.typing import NDArray

TFRegion = NDArray[np.complex128] # shape (channels, time, frequency)

def expectation(x: NDArray) -> NDArray:
    return x

def cross_correlation(Xi: TFRegion, Xj: TFRegion, lamb: float) -> TFRegion:
    assert Xi.dtype == Xj.dtype == np.complex128
    sigma_ij = np.zeros_like(Xi)

    # Note: when m==0, m-1 will take the final time slice. It shouldn't
    # really do that mathematically, but it will be zeros anyway. 
    for m in np.arange(sigma_ij.shape[0]):
        sigma_ij[m] = ((1-lamb) * sigma_ij[m-1]) + (lamb * Xi[m] * Xj[m].conj())
    
    return sigma_ij

def ambiance_index(X: TFRegion, lamb: float = 0.1) -> TFRegion:
    sigma_12 = cross_correlation(X[0], X[1], lamb)
    sigma_11 = cross_correlation(X[0], X[0], lamb).real
    sigma_22 = cross_correlation(X[1], X[1], lamb).real
    sigma = np.abs(sigma_12) / np.pow((sigma_11 * sigma_22), 0.5)
    return 1 - sigma

def panning_index(X: TFRegion) -> TFRegion:
    psi_12 = cross_correlation(X[0], X[1], 1.)
    psi_11 = cross_correlation(X[0], X[0], 1.).real
    psi_22 = cross_correlation(X[1], X[1], 1.).real
    psi = 2 * np.abs(psi_12) / (psi_11 + psi_22)
    psi_1 = np.abs(psi_12) / psi_11
    psi_2 = np.abs(psi_12) / psi_22
    delta_hat = np.sign(psi_1 - psi_2)
    print(psi_12.dtype, psi.dtype, psi_1.dtype, psi_2.dtype)
    return (1 - psi) * delta_hat