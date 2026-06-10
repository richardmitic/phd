from pathlib import Path
import pyfar as pf
import numpy as np

from algorithms.common import chunked, TFRegion
from algorithms import gomez, sarroff, tardieu

import pytest

@pytest.fixture
def test_audio_file_path() -> Path:
    return Path.home() / "Music/fma_small/040/040139.mp3"
    # return Path.home() / "Music/fma_small/040/040122.mp3"

@pytest.fixture
def test_audio(test_audio_file_path: Path) -> pf.Signal:
    signal = pf.dsp.time_crop(pf.io.read_audio(test_audio_file_path), [0,5], unit='s')
    # signal.time[0] *= 0.5
    return signal

@pytest.fixture
def test_spectrogram(test_audio: pf.Signal) -> TFRegion:
    return np.fft.rfft(chunked(test_audio, 1024, 512))


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


    