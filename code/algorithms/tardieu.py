from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray
import pyfar as pf
from scipy.signal import hilbert, butter, filtfilt

from python_auditory_toolbox import auditory_toolbox as pat

from .common import chunked, TFRegion

Cochleagram = NDArray[np.float64] # shape (channel, time, frequency)
SSPS = NDArray[np.float64] # shape (channel, time, frequency)

@dataclass
class AmplitudeStereoFeatures:
    global_amount_of_panning: float
    global_amount_of_panning_variation: float
    mean_over_time: NDArray[np.float64]
    mean_over_time_absolute: NDArray[np.float64]
    std_over_time: NDArray[np.float64]


def modulate_envelope(x: NDArray[np.float64]) -> NDArray[np.float64]:
    envelope = np.power(np.abs(hilbert(x)), 0.23)
    return x * envelope

def extract_envelope(x: NDArray[np.float64], sampling_rate: float) -> NDArray[np.float64]:
    x = modulate_envelope(x)
    x *= np.sign(x) # half wave rectify
    x = np.sqrt(x) # square root
    
    # lowpass
    fc = 800
    b, a = butter(4, fc/sampling_rate, btype='low', analog=False)
    return filtfilt(b, a, x)

def make_subbands(audio: pf.Signal, num_bands: int) -> NDArray[np.float64]:
    coefs = pat.MakeErbFilters(audio.sampling_rate, num_bands, low_freq=30)
    return np.stack([pat.ErbFilterBank(chan, coefs) for chan in audio.time])


def make_cochleagram(envelope:NDArray[np.float64], chunk_size: int, hop_size: int) -> NDArray[np.float64]:
    chunks = np.stack([chunked(chan, chunk_size, hop_size) for chan in envelope]) # shape (channel, freq_band, chunk, sample)
    cochleagram = chunks.mean(axis=-1)
    return cochleagram


def cochleagram(audio: pf.Signal, chunk_time: float, hop_time: float, num_bands: int) -> Cochleagram:
    x = make_subbands(audio, num_bands)
    envelope = extract_envelope(x, audio.sampling_rate)
    
    chunk_size = int(chunk_time * audio.sampling_rate)
    hop_size = int(hop_time * audio.sampling_rate)
    return make_cochleagram(envelope, chunk_size, hop_size)


def ssps(audio: pf.Signal, chunk_time: float, hop_time: float, num_bands: int) -> SSPS:
    subband_signals = make_subbands(audio, num_bands) # shape (channel, frequency, time)
    chunk_size = int(chunk_time * audio.sampling_rate)
    hop_size = int(hop_time * audio.sampling_rate)
    chunks = np.stack([chunked(chan, chunk_size, hop_size) for chan in subband_signals]) # shape (channel, freq_band, chunk, sample)
    mid = chunks[1] + chunks[0]
    side = chunks[1] - chunks[0]
    std_mid = np.std(mid, axis=-1)
    std_side = np.std(side, axis=-1)
    return std_side / std_mid

def ssps_stft(spect: TFRegion, fft_size: int, sample_rate: float) -> SSPS:
    frequency = np.fft.rfftfreq(fft_size, d=1/sample_rate)
    print(np.min(frequency), np.max(frequency))
    # t = np.linspace(0,1, sample_rate)[:fft_size]
    t = np.arange(0,fft_size)
    
    phi_l = np.angle(spect[0])
    phi_r = np.angle(spect[1])
    amp = np.mean(np.abs(spect), axis=0)
    

    M = phi_l.shape[0]
    K = phi_l.shape[1]
    Sl = np.zeros((M, K, fft_size))
    Sr = np.zeros((M, K, fft_size))

    for m in range(M): # time step
        for k in range(K): # frequency band
            fk = frequency[k]
            x = ((2 * np.pi * fk) / sample_rate)
            # print(np.min(time), np.max(time))
            Sl[m,k] = np.cos((x * t) + phi_l[m,k])
            Sr[m,k] = np.cos((x * t) + phi_r[m,k])

    import matplotlib.pyplot as plt
    numerator = np.ma.masked_invalid(np.std(Sl - Sr, axis=-1))
    denominator = np.ma.masked_invalid(np.std(Sl + Sr, axis=-1))

    sigma_lr = numerator / denominator
    print(sigma_lr.shape)
    print(np.min(sigma_lr), np.max(sigma_lr))
    plt.imshow(np.rot90(np.log(sigma_lr)), aspect='auto')
    plt.show()
    # S = np.cos((angular_frequnecy * time) + phase)
    # print(S.shape)


def amplitude_stereo_features(
    coch: Cochleagram
) -> AmplitudeStereoFeatures:
    cd = coch[1] - coch[0]  # right - left
    return AmplitudeStereoFeatures(
        global_amount_of_panning=np.mean(np.abs(cd)),
        global_amount_of_panning_variation=np.std(np.abs(cd)),
        mean_over_time=np.mean(cd, axis=1),
        mean_over_time_absolute=np.mean(np.abs(cd), axis=1),
        std_over_time=np.std(cd, axis=1),
    )
