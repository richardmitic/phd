from typing import Tuple
import numpy as np
from numpy.typing import NDArray
import pyfar as pf

from algorithms.common import chunked, AudioRegion

def box_counting(
    signal: pf.Signal | AudioRegion, 
    nboxes: int = 10 # number of boxes in 1 direction of 1 axis. Maximum possible boxes is (2N)^2
) -> float:
    if isinstance(signal, pf.Signal):
        signal = signal.time
    quantized_signal = (signal * nboxes).astype(int)
    max_boxes = (2 * nboxes) ** 2
    return np.unique(quantized_signal.T, axis=0).shape[0] / max_boxes

def correlation(signal: pf.Signal | AudioRegion) -> float:
    # This formula is directly from Ziemer's paper.
    # See here for a nice explanation of the covariance matrix
    # https://users.cs.utah.edu/~tch/CS4640F2019/resources/A%20geometric%20interpretation%20of%20the%20covariance%20matrix.pdf
    if isinstance(signal, pf.Signal):
        signal = signal.time
    return np.min(np.corrcoef(*signal))


def feature_vectors(
    signal: pf.Signal, 
    chunk_duration: float, 
    hop_duration: float
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    chunk_samples = int(chunk_duration * signal.sampling_rate)
    hop_samples = int(hop_duration * signal.sampling_rate)
    chunks = chunked(signal, chunk_samples, hop_samples)
    box_counting_vector = []
    correlation_vector = []
    for i in range(chunks.shape[1]):
        chunk = chunks[:, i, :]
        box_counting_vector.append(box_counting(chunk))
        correlation_vector.append(correlation(chunk))
    return np.array(box_counting_vector), np.array(correlation_vector)