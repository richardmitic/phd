from pathlib import Path
import pyfar as pf
import numpy as np
import matplotlib.pyplot as plt

from algorithms.common import chunked, make_spectrogram, split_spectrogram_bands, TFRegion
from algorithms import gomez, sarroff, tardieu, ziemer, tzanetakis, sip

import pytest

@pytest.fixture
def test_audio_file_path() -> Path:
    return Path.home() / "Music/fma_small/040/040139.mp3"
    # return Path.home() / "Music/fma_small/040/040122.mp3"

@pytest.fixture
def test_audio(test_audio_file_path: Path) -> pf.Signal:
    signal = pf.dsp.normalize(
        pf.dsp.time_crop(
            pf.io.read_audio(test_audio_file_path), 
            [0,5], 
            unit='s'
        ),
        domain = 'time',
        target=1.,
        reference_method='max'
    )
    # signal.time[0] *= 0.5
    return signal


@pytest.fixture
def test_spectrogram(test_audio: pf.Signal) -> TFRegion:
    return make_spectrogram(test_audio)


def _debug_ph(ph):
    import matplotlib.pyplot as plt
    plt.plot(ph)
    plt.show()

def _debug_img(img):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2,1)
    vmin, vmax = np.min(img), np.max(img)
    ax[0].imshow(img[0], aspect='auto', vmin=vmin, vmax=vmax)
    ax[1].imshow(img[1], aspect='auto', vmin=vmin, vmax=vmax)
    plt.show()

def test_gomez_ph(test_spectrogram: TFRegion):
    ph = gomez.panning_histogram(test_spectrogram, 31)
    # _debug_ph(ph)
    assert all(ph > 0.)
    # Peak panning is somewhere near the middle, but not necessarily the centre bin
    assert 14 <= np.argmax(ph) <= 16

def test_sarroff_ph(test_spectrogram: TFRegion):
    ph = sarroff.panning_histogram(np.abs(test_spectrogram), 15)
    # _debug_ph(ph)
    assert all(ph > 0.)
    # Peak panning is somewhere near the middle, but not necessarily the centre bin
    assert 14 <= np.argmax(ph) <= 16

def test_sarroff_ph_width(test_spectrogram: TFRegion):
    ph = sarroff.panning_histogram(np.abs(test_spectrogram), 65)


def test_cochleagram():
    left = pf.signals.sine(100., 44100 * 5)
    right = pf.signals.sine(1000., 44100 * 5)
    signal = pf.Signal(np.stack([left.time[0], right.time[0] * 0.5]), sampling_rate=left.sampling_rate)
    coch = tardieu.cochleagram(signal, 0.02, 0.01, 32)
    # _debug_img(coch)
    assert coch.shape[:2] == (2,32)
    # lowest frequency band in the left channel should be the highest amplitude
    assert (np.argmax(coch, axis=1)[0] == 31).all()
    # A different frequency band in the right channel should be the highest amplitude
    assert (np.argmax(coch, axis=1)[1] == 21).all()
    # Left should be louder than right
    assert np.max(coch[0]) > np.max(coch[1])

def test_chunks_stereo():
    audio = np.arange(12).reshape(2,-1)
    assert np.array_equal(
        audio,
        [
            [0,1,2,3,4,5],
            [6,7,8,9,10,11]
        ]
    )
    chunks = chunked(audio, 2,1)
    assert np.array_equal(
        chunks,
        [
            [[0,1],[1,2],[2,3],[3,4],[4,5]],
            [[6,7],[7,8],[8,9],[9,10],[10,11]]
        ])


def test_chunks_mono():
    audio = np.arange(6)
    chunks = chunked(audio, 2,1)
    assert np.array_equal(
        chunks,
        [[0,1],[1,2],[2,3],[3,4],[4,5]],
    )

# def test_fa_analysis_signal(test_spectrogram: TFRegion):
#     hists = sarroff.panning_histogram_region(np.abs(test_spectrogram), 15)
#     print(hists.shape)
#     import matplotlib.pyplot as plt
#     import scipy.signal as ss
#     fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
#     # X, Y = np.meshgrid(np.arange(hists.shape[1]), np.arange(20))
#     kernel = np.ones((20,1))
#     print(hists.shape, kernel.shape)
#     filtered_hists = ss.convolve(hists, kernel)[::20,:]
#     for i in range(len(filtered_hists)):
#         x = np.ones(filtered_hists.shape[1]) * i
#         y = np.arange(filtered_hists.shape[1])
#         z = filtered_hists[i]
#         ax.plot(x,y,z, color='k')
#     plt.show()

def test_goniometer_box_counting(test_audio: pf.Signal):
    assert 0.5 < ziemer.box_counting(test_audio) < 1

def test_goniometer_correlation(test_audio: pf.Signal):
    assert -0.5 < ziemer.correlation(test_audio) < 0.5

def test_goniometer_feature_vectors():
    left = pf.signals.sine(100, 44100)
    right = pf.signals.sine(100, 44100)
    lfo = pf.signals.sine(1, 44100)
    right = pf.multiply((right, lfo), domain='time')
    test_audio = pf.utils.concatenate_channels([left, right])

    box, corr = ziemer.feature_vectors(test_audio, 0.02, 0.02)

    # All box counts and correlations should be within the proper ranges
    assert all(box >= 0)
    assert all(box <= 1)
    assert all(corr >= -1)
    assert all(corr <= 1)

    # The right channel flips polarity half way, so correlation should start positive and end negative
    assert 0.9 < corr[5] < 1
    assert -1 < corr[-5] < -0.9

def _triangle(time, freq: float, phase: float):
    phasor = ((time * freq) + phase) % 1.
    flip = phasor > 0.5
    phasor[flip] = 1 - phasor[flip]
    phasor *= 2
    return phasor
    

def _make_spf_signal(panning_speed: float, panning_amount: float) -> pf.Signal:
    N = 44100 * 4
    time = np.linspace(0,4,N)
    beep = np.sin(time * 2 * np.pi * 100)
    tri = _triangle(time, panning_speed, 0.)
    tri = ((tri - 0.5) * panning_amount) + 0.5
    left_amp = np.cos(0.5 * np.pi * tri)
    right_amp = np.sin(0.5 * np.pi * tri)
    panned_beep = pf.Signal(np.stack([beep * left_amp, beep * right_amp]), sampling_rate=44100)
    return panned_beep


def test_spf():
    signal1 = _make_spf_signal(2., 1)
    signal2 = _make_spf_signal(2., 0.2)
    signal3 = _make_spf_signal(10., 0.2)
    spect1 = make_spectrogram(signal1)
    spect2 = make_spectrogram(signal2)
    spect3 = make_spectrogram(signal3)
    spf1 = tzanetakis.stereo_panning_features(spect1, signal1.sampling_rate, 40)
    spf2 = tzanetakis.stereo_panning_features(spect2, signal2.sampling_rate, 40)
    spf3 = tzanetakis.stereo_panning_features(spect3, signal3.sampling_rate, 40)

    # check that the signal with more panning added has a higher average panning
    idx = 0 # full band, running mean, mean
    assert spf1[idx] > spf2[idx]
    
    # check that the signal with fast panning has a higher short-term panning
    idx = 4 # full band, running std, mean
    assert spf3[idx] > spf2[idx]


# @pytest.mark.skip
def test_cli(test_audio: pf.Signal):
    from python_auditory_toolbox import auditory_toolbox as pat
    fc = pat.ErbSpace(low_freq=20, high_freq=test_audio.sampling_rate/2, n=24)
    bands = np.flipud(np.stack([fc[1:], fc[:-1]]).T)
    print(bands)
    # bands = [[0,200],[200,400],[400,800],[800,1600],[1600,3200],[3200,6400],[6400,12800]]
    s = sip.sip(
        test_audio, 
        1024, 
        512, 
        33, 
        bands,
    )
    plt.imshow(np.flipud(s), aspect='auto', interpolation='gaussian')
    plt.show()

def test_spect_subbands(test_spectrogram: TFRegion):
    bands = np.array([
        [0,250],
        [250,2500],
        [2500,20000]
    ])
    assert test_spectrogram.shape == (2, 429, 513)
    subs = split_spectrogram_bands(test_spectrogram, bands, 1024, 44100)
    assert subs[0].shape == (2, 429, 6)
    assert subs[1].shape == (2, 429, 53)
    assert subs[2].shape == (2, 429, 406)
    
def test_sip(test_audio: pf.Signal):
    bands = np.array([
        [0,250],
        [250,2500],
        [2500,20000]
    ])
    s_gomez = sip.sip(test_audio, 1024, 512, 33, bands, algorithm='gomez')
    s_sarroff = sip.sip(test_audio, 1024, 512, 33, bands, algorithm='sarroff')
    assert s_gomez.shape == (3,33)
    assert s_sarroff.shape == (3,33)


def test_asf(test_audio: pf.Signal):
    coch = tardieu.cochleagram(test_audio, 0.04, 0.02, 70)
    asf = tardieu.amplitude_stereo_features(coch)
    assert asf.global_amount_of_panning > 0
    assert asf.global_amount_of_panning_variation > 0
    assert asf.mean_over_time.shape == (70,)
    assert asf.mean_over_time_absolute.shape == (70,)
    assert asf.std_over_time.shape == (70,)

@pytest.mark.skip
def test_ssps(test_spectrogram: TFRegion):
    # left = pf.signals.files.speech()
    # right = pf.dsp.time_shift(left, 0.01, unit='s')
    # stereo = pf.utils.concatenate_channels([left, right])
    # set_samples = int(stereo.sampling_rate * 2)
    # stereo.time[1, :set_samples] = stereo.time[0, 20:set_samples+20] # begin in phase and then go out of phase
    # pf.io.write_audio(stereo, "ssps.wav")
    # ssps = tardieu.ssps(stereo, 0.04, 0.02, 70)
    # plt.imshow(ssps, aspect='auto')
    # plt.show()
    ssps = tardieu.ssps_stft(test_spectrogram, 1024, 44100)
    