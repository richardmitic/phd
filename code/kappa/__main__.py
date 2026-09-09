import matplotlib.pyplot as plt
import pyfar as pf
import numpy as np
from python_auditory_toolbox import auditory_toolbox as pat
import scipy
import librosa
import pandas as pd
from pathlib import Path
from subprocess import check_output
import subprocess
from matplotlib.patches import ConnectionPatch
from matplotlib.colors import LightSource
from matplotlib.collections import LineCollection
import math
import typer
from numpy.typing import NDArray

from cache_to_disk import cache_to_disk
from typing import Tuple, Any

from algorithms import (
    avendano,
    gomez,
    sarroff,
    tardieu,
    common,
    tzanetakis,
    ziemer,
    display,
    cochleagram,
)


def _git_root() -> Path:
    return Path(check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip())


def _ensure_dir(dir: Path):
    dir.mkdir(exist_ok=True)


def _maybe_print(x: Any):
    if x is not None:
        print(x)

def _to_dat(X: NDArray[np.float64], Y: NDArray[np.float64]) -> str:
    return '\n'.join([f"{round(x, 3)} {round(y, 3)}" for x,y in zip(X,Y)])

# Main app. Smaller functions can be called as individual comamnds
app = typer.Typer(result_callback=_maybe_print)

# default matplotlib style
plt.rcParams["font.family"] = "Times"
plt.rcParams["font.size"] = 9

# Default parameters
OUTPUT_DIR = _git_root() / "papers/kappa/generated"
ANNOTATION_BBOX_PROPS = dict(boxstyle="round", facecolor="white", alpha=0.9)

# This linewidth value was printed from the latex UUThesisTemplate class
LATEX_LINEWIDTH = 4.72533

# Standardized lengths
GOLDEN_RATIO = 0.618
WIDE = LATEX_LINEWIDTH
MID_WIDE = LATEX_LINEWIDTH * np.sqrt(GOLDEN_RATIO)
MID = LATEX_LINEWIDTH * GOLDEN_RATIO
NARROW = LATEX_LINEWIDTH * GOLDEN_RATIO**2

# Standardized rectangle sizes
WIDE_RECT = (WIDE, MID)
WIDE_SKINNY_RECT = (WIDE, NARROW)
MID_WIDE_RECT = (MID_WIDE, NARROW)
MID_RECT = (MID, NARROW)
WIDE_SQUARE = (WIDE, WIDE)
MID_WIDE_SQUARE = (MID_WIDE, MID_WIDE)
MID_SQUARE = (MID, MID)


@app.command()
def get_demo_tracks() -> pd.DataFrame:
    fma_metadata = pd.read_csv(
        "/Users/richard/Music/fma_metadata/tracks.csv", index_col=0, header=[0, 1]
    )
    fma_genres = pd.read_csv(
        "/Users/richard/Music/fma_metadata/raw_genres.csv", index_col=0
    )
    track_ids = [123899, 117614, 122809]  # chosen manually
    demo_tracks = fma_metadata.loc[track_ids]
    demo_tracks["local", "filepath"] = demo_tracks.index.map(
        lambda x: Path(f"/Users/richard/Music/fma_small/{str(x)[:3]}/{x}.mp3")
    )
    demo_tracks["local", "letter"] = list("ABC")
    demo_tracks = demo_tracks[
        [
            ("artist", "name"),
            ("track", "title"),
            ("track", "genres"),
            ("local", "filepath"),
            ("local", "letter"),
        ]
    ]
    demo_tracks[("track", "genres")] = demo_tracks[("track", "genres")].map(
        lambda genre_list: [fma_genres.loc[g, "genre_title"] for g in eval(genre_list)]
    )
    return demo_tracks


@app.command()
def get_freesound_clips() -> pd.DataFrame:
    name = ["kick", "hihat", "speech"]
    freesound_id = [581451, 581473, 31912]
    freesound_dir = Path.home() / "Music/freesound"
    filepath = [
        freesound_dir / "581451__johnnydekk__fractanimal_acoustic_drum_kit_kick_2.wav",
        freesound_dir
        / "581473__johnnydekk__fractanimal_acoustic_drum_kit_high_hat_3.wav",
        freesound_dir / "31912__acclivity__globalwarming_marg.wav",
    ]
    user = ["johnnydekk", "johnnydekk", "acclivity"]
    url = [
        f"https://freesound.org/people/{user}/sounds/{id}"
        for user, id in zip(user, freesound_id)
    ]
    return pd.DataFrame(
        data=dict(name=name, filepath=filepath, user=user, url=url), index=freesound_id
    )


def get_hrirs(
    angle: float = 60
) -> Tuple[pf.Signal, pf.Signal]:
    hrirs, sources = pf.signals.files.head_related_impulse_responses(
        position="horizontal", diffuse_field_compensation=True
    )
    elevation = 0
    np.radians(angle)
    azimuth_L = np.radians(angle)
    azimuth_R = -azimuth_L
    radius = 1

    desired_direction_L = pf.Coordinates.from_spherical_elevation(
        azimuth_L, elevation, radius
    )
    desired_direction_R = pf.Coordinates.from_spherical_elevation(
        azimuth_R, elevation, radius
    )

    index_L, _ = sources.find_nearest(desired_direction_L)
    index_R, _ = sources.find_nearest(desired_direction_R)

    return hrirs[index_L], hrirs[index_R]


@app.command()
def make_brir_dats(output_dir: Path = OUTPUT_DIR):
    _, hrir_R = get_hrirs(angle=30)
    n = 64
    start = 10
    hrir_R = pf.dsp.time_crop(hrir_R, [start, start+n])
    X = np.arange(n)

    (output_dir / "brir_L.dat").write_text(_to_dat(X, hrir_R.time[0]))
    (output_dir / "brir_R.dat").write_text(_to_dat(X, hrir_R.time[1]))


@app.command()
def make_ild_itd_dats(output_dir: Path = OUTPUT_DIR) -> float:
    a = 1.99
    rv = scipy.stats.gamma(a)
    x = np.linspace(0, 10, 200)
    y = rv.pdf(x) * np.cos(8*x) - 0.5
    y2 = rv.pdf(x-1) * np.cos(8*(x-1)) + 0.5
    y3 = (y*0.5) + 0.75

    (output_dir / "itd_R.dat").write_text(_to_dat(x,y))
    (output_dir / "itd_L.dat").write_text(_to_dat(x,y2))
    (output_dir / "ild_R.dat").write_text(_to_dat(x,y))
    (output_dir / "ild_L.dat").write_text(_to_dat(x,y3))

    return max(rv.pdf(x))

@app.command()
def draw_panned_drums(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_RECT,
):
    hrir_L, hrir_R = get_hrirs()
    fs_clips = get_freesound_clips()
    kick = pf.io.read_audio(fs_clips.iloc[0].filepath)
    hihat = pf.io.read_audio(fs_clips.iloc[1].filepath)

    fig, ax = plt.subplots(2, 1, figsize=figsize, sharex=True, layout="constrained")

    def _render(audio, hrir, ax):
        binaural_audio = pf.dsp.convolve(audio, hrir)
        cropped = pf.dsp.time_crop(binaural_audio, [0, 0.03], unit="s")
        cropped.time[0] += 1
        cropped.time[1] -= 1
        X = cropped.times * 1000
        ax.plot(X, cropped.time[0], label="Left", color="k", linewidth=0.5)
        ax.plot(X, cropped.time[1], label="Right", color="k", linewidth=0.5)
        ax.set_ylim(-2, 2)
        ax.set_yticks([1, -1], labels=["L", "R"])
        ax.grid(True, which="both", linestyle="dotted")

    _render(hihat, hrir_R, ax[0])
    _render(kick, hrir_R, ax[1])

    ax[0].set_xlabel(None)
    ax[1].set_xlabel("Time (ms)")

    x = 0.02
    y = 0.93
    ax[0].text(
        x,
        y,
        "Hi-hat",
        transform=ax[0].transAxes,
        verticalalignment="top",
        bbox=ANNOTATION_BBOX_PROPS,
    )
    ax[1].text(
        x,
        y,
        "Kick",
        transform=ax[1].transAxes,
        verticalalignment="top",
        bbox=ANNOTATION_BBOX_PROPS,
    )

    fig.savefig(output_dir / "hihat_kick.pdf")


@app.command()
def draw_nyquist(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_SKINNY_RECT,
):
    # There's a lot of mathtext in this diagram and the it looks
    # much better to render it with TeX
    with plt.rc_context({"text.usetex": True, "font.family": "Times"}):
        fig, ax = plt.subplots(2, 1, figsize=figsize, sharex=True, layout="constrained")
        x1 = np.linspace(0, 2 * np.pi, 1000)
        x2 = np.linspace(0, 2 * np.pi, 7)

        f = 3
        df = 2.5

        y1 = np.cos(x1 * f)
        y11 = np.cos(x2 * f)
        y2 = np.cos(x1 * (f - df))
        y22 = np.cos(x2 * (f - df))
        y3 = np.cos(x1 * (f + df))
        y33 = np.cos(x2 * (f + df))

        def _setup_axes(ax: plt.Axes, ylim: Tuple[float, float]):
            ax.spines["top"].set_color("none")
            ax.spines["right"].set_color("none")
            ax.spines["left"].set_color("none")
            # ax.spines['bottom'].set_position(('data', 0))
            ax.spines["bottom"].set_color("none")
            ax.set_yticks([])
            ax.set_xticks([])
            ax.set_xlim(-0.1, 6.4)
            ax.set_ylim(*ylim)

        markers = dict(
            markerfacecolor="none",
            markeredgewidth=0.5,
            markersize=6,
            marker="o",
            linestyle="none",
        )

        for x in x2:
            con = ConnectionPatch(
                xyA=(x, 1),
                xyB=(x, -1),
                coordsA="data",
                coordsB="data",
                axesA=ax[0],
                axesB=ax[1],
                color="k",
                linestyle=(0, (0.5, 5)),
                linewidth=0.5,
            )
            ax[1].add_artist(con)

        ax[1].plot(x1, y2, color="k", linewidth=0.618)
        ax[1].plot(x2, y22, color="k", **markers)
        ax[1].plot(x1, y3, color="k", linewidth=0.618)
        ax[1].plot(x2, y33, color="k", **markers)

        ax[0].plot(x1, y1, color="k", linewidth=0.618)
        ax[0].plot(x2, y11, color="k", **markers)

        for i in range(3):
            ax[0].text(x=x2[i], y=1.4, s=f"$n={i}$", ha="center", va="center")

        ax[1].text(x=x2[0], y=-1.4, s=f"$t=0$", ha="center", va="center")
        ax[1].text(x=x2[1], y=-1.4, s=f"$t=T_s$", ha="center", va="center")
        ax[1].text(x=x2[2], y=-1.4, s=f"$t=2T_s$", ha="center", va="center")

        ax[0].text(x=x2[3], y=1.4, s=f"$\dots$", ha="center", va="center")
        ax[1].text(x=x2[3], y=-1.4, s=f"$\dots$", ha="center", va="center")

        ax[1].set_ylabel(
            "$f_N \pm f_\delta$",
            rotation=0,
            horizontalalignment="right",
            verticalalignment="center",
        )
        ax[0].set_ylabel(
            "$f_N$", rotation=0, horizontalalignment="right", verticalalignment="center"
        )

        _setup_axes(ax[0], (-1.2, 1.2))
        _setup_axes(ax[1], (-1.2, 1.2))

        fig.savefig(output_dir / "nyquist.pdf")


@app.command()
def draw_equal_power_panning(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = MID_WIDE_RECT,
):
    fig, ax = plt.subplots(1, 1, figsize=figsize, layout="constrained")
    a = np.linspace(0, 1, 100)
    gl = np.cos(0.5 * np.pi * a)
    gr = np.sin(0.5 * np.pi * a)
    total = np.sqrt(gl**2 + gr**2)

    cmap = plt.colormaps.get_cmap("berlin")
    cl, cc, cr = cmap([0, 128, 256])

    centre_gain = 1 / np.sqrt(2)

    ax.plot(a, gl, color=cl, label="Left channel")
    ax.plot(a, gr, color=cr, label="Right channel")
    ax.plot(a, total, "--", color=cc, label="Perceived loudness", linewidth=0.618)
    ax.set_xticks([0, 0.5, 1], labels=["0\n(Left)", "0.5\n(Centre)", "1\n(Right)"])
    ax.set_yticks([0, centre_gain, 1], labels=[0, "$\\frac{1}{\sqrt{2}}$", 1])
    ax.set_xlabel("Panning factor")
    ax.set_ylabel("Amplitude")
    ax.hlines([centre_gain], 0, 0.5, color="k", linestyles="dotted", linewidth=0.5)
    ax.vlines([0.5], 0, centre_gain, color="k", linestyles="dotted", linewidth=0.5)
    # ax.set_ybound(0, 1.2)

    # ax.text(x=0, y=1.05, s="Left channel")
    # ax.text(x=1, y=1.05, s="Right channel", horizontalalignment="right")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", borderaxespad=0.0)

    fig.savefig(output_dir / "equal_power_panning.pdf")


@app.command()
def draw_spectrogram_comparison(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_SQUARE,
    single_plot_figsize: Tuple[float, float] = WIDE_SKINNY_RECT,
):
    _ensure_dir(output_dir)
    fig, ax = plt.subplots(3, 1, figsize=figsize, sharex=True, layout="constrained")

    signal = pf.io.read_audio(
        Path.home() / "Music/freesound/31912__acclivity__globalwarming_marg.wav"
    )
    audio, sr = signal.time[0], signal.sampling_rate

    start, end = 0.8, 2.6
    duration = end - start
    audio = audio[int(start * sr) : int(end * sr)]

    stft_bands = 2048
    num_bands = 32

    def _kilo_formatter(x):
        if x < 1000:
            return str(int(x))
        else:
            return f"{int(x / 1000)}k"

    linear_freqs = np.fft.rfftfreq(stft_bands, d=1 / sr)

    erb_freqs, coch = cochleagram.cochleagram(pf.dsp.time_crop(signal, [start, end], unit='s'), num_bands, 0.02, 0.01)

    # erb_freqs = pat.ErbSpace(low_freq=100, high_freq=sr / 2, n=num_bands)[::-1]

    # coefs = pat.MakeErbFilters(sr, num_bands, low_freq=100)
    # y = pat.ErbFilterBank(audio, coefs)
    # y *= np.sign(y)  # half wave rectify
    # y = np.sqrt(y)  # square root

    # # low pass
    # fc = 800
    # b, a = scipy.signal.butter(4, fc / sr, btype="low", analog=False)
    # y = scipy.signal.filtfilt(b, a, y)

    # coch_chunk_length = 0.02
    # chunk_size = int(coch_chunk_length * sr)
    # hop_size = int(0.5 * chunk_size)
    # chunks = np.lib.stride_tricks.sliding_window_view(y, chunk_size, axis=1)[
    #     :, ::hop_size, :
    # ]
    # # coch = np.sqrt(np.sum(np.pow(chunks, 2), axis=(2,))) # RMS
    # coch = librosa.amplitude_to_db(np.mean(chunks, axis=2))

    D = np.abs(librosa.stft(audio, n_fft=stft_bands)) ** 2
    S = librosa.feature.melspectrogram(S=D, sr=sr, n_mels=num_bands)
    D = np.flipud(D)
    S = np.flipud(S)
    mel_freqs = librosa.mel_frequencies(n_mels=num_bands, fmax=sr / 2)

    images = []

    desired_ticks = [100, 500, 1000, 2000, 5000, 10000, 20000]

    def _draw_stft_spect(ax, spect):
        img = ax.imshow(
            librosa.power_to_db(spect, ref=np.max),
            aspect="auto",
            cmap="magma",
            extent=(0, duration, 0, linear_freqs[-1]),
        )
        ax.set_yticks(
            [0, 5000, 10000, 15000, 20000], labels=["0", "5k", "10k", "15k", "20k"]
        )
        return img

    def _draw_mel_spect(ax, spect):
        img = ax.imshow(
            librosa.power_to_db(spect, ref=np.max),
            aspect="auto",
            cmap="magma",
            extent=(0, duration, 0, num_bands),
        )
        yticks = np.interp(desired_ticks, mel_freqs, np.arange(num_bands))
        yticklabels = [_kilo_formatter(x) for x in desired_ticks]
        ax.set_yticks(yticks, labels=yticklabels)
        return img

    def _draw_coch_spect(ax, spect):
        img = ax.imshow(
            spect, aspect="auto", cmap="magma", extent=(0, duration, 0, num_bands)
        )
        yticks = np.interp(desired_ticks, erb_freqs, np.arange(num_bands))
        yticklabels = [_kilo_formatter(x) for x in desired_ticks]
        ax.set_yticks(yticks, labels=yticklabels)
        return img

    images.append(_draw_stft_spect(ax[0], D))
    images.append(_draw_mel_spect(ax[1], S))
    images.append(_draw_coch_spect(ax[2], coch))

    ax[0].set_ylabel("Frequency (Hz)")
    ax[1].set_ylabel("Frequency (Hz)")
    ax[2].set_ylabel("Frequency (Hz)")
    ax[2].set_xlabel("Time (s)")

    x = 0.02
    y = 0.94
    for i, txt in enumerate(["STFT Spectrogram", "Mel Spectrogram", "Cochleagram"]):
        ax[i].text(
            x,
            y,
            txt,
            transform=ax[i].transAxes,
            verticalalignment="top",
            bbox=ANNOTATION_BBOX_PROPS,
        )
    fig.colorbar(images[0], ax=ax, label="Normalized sound intensity", ticks=[])

    fig.savefig(output_dir / "spect_comp.pdf")

    # Now do individual diagrams
    for draw_func, spect, filename in zip(
        [_draw_stft_spect, _draw_mel_spect, _draw_coch_spect],
        [D, S, coch],
        ["stft_spect.pdf", "mel_spect.pdf", "cochleagram.pdf"],
    ):
        fig, ax = plt.subplots(1, 1, figsize=single_plot_figsize, layout="constrained")
        img = draw_func(ax, spect)
        fig.colorbar(img, ax=ax, label="Sound intensity (dB)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_xlabel("Time (s)")
        fig.savefig(output_dir / filename)


@app.command()
def draw_gammatone_filters(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = MID_RECT,
    fs=44100,
    fft_length=4096 * 4,
    fmin=20,
    num_bands=8,
):
    fcoefs = pat.MakeErbFilters(fs, num_bands, low_freq=fmin)
    impulse_len = fft_length
    x = np.zeros(impulse_len)
    x[0] = 1
    y = pat.ErbFilterBank(x, fcoefs)
    take_len = impulse_len // 2
    resp = 20 * np.log10(np.abs(np.fft.fft(y.T, axis=0)))[:take_len]

    fig, ax = plt.subplots(1, 1, figsize=figsize, layout="constrained")

    ax.semilogx(
        np.arange(take_len) * (fs / impulse_len), resp, color="k", linewidth=0.618
    )
    ax.set_xlim(20, fs / 2)
    ax.set_ylim(-60, 0)
    ax.set_ylabel("Filter response (dB)")
    ax.set_xlabel("Frequency (Hz)")

    fig.savefig(output_dir / "gammatone_filterbank.pdf")


@app.command()
def draw_mel_filters(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = MID_WIDE_RECT,
    fs=44100,
    fft_length=4096,
    fmin=20,
    num_bands=8,
):

    freqs = np.fft.rfftfreq(fft_length, d=1 / fs)
    F = np.tile(freqs, (num_bands, 1))

    mel_filters = librosa.filters.mel(
        sr=fs, n_fft=fft_length, n_mels=num_bands, fmin=fmin
    )
    mel_filters /= np.max(mel_filters)
    mel_filters[mel_filters == 0] = (
        np.nan
    )  # showing all the zero weights looks cluttered, so just get rid of them

    fig, ax = plt.subplots(1, 2, figsize=figsize, sharey=True, layout="constrained")
    ax[0].plot(F.T, mel_filters.T, color="k", linewidth=0.618)
    ax[1].semilogx(F.T, mel_filters.T, color="k", linewidth=0.618)
    ax[0].set_xticks(
        [0, 5000, 10000, 15000, 20000], labels=["0", "5k", "10k", "15k", "20k"]
    )
    ax[0].set_ylabel("Filter weight")
    ax[0].set_xlabel("Frequency (Hz, linear)")
    ax[1].set_xlabel("Frequency (Hz, logarithmic)")
    # ax[0].set_title("Mel filterbank (linear frequency)")
    # ax[1].set_title("Mel filterbank (logarithmic frequency)")

    fig.savefig(output_dir / "mel_filterbank.pdf")


@app.command()
def draw_cochleagram_steps(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_SKINNY_RECT,
):
    audio = pf.signals.exponential_sweep_time(4410, [100, 20000])
    subbands = tardieu.make_subbands(audio, 8)[0]  # shape (channel, subband, time)
    envelope = tardieu.extract_envelope(
        subbands, audio.sampling_rate
    )  # shape (subband, time)
    coch = tardieu.make_cochleagram(envelope, 1024, 512)
    # freqs = np.round(pat.ErbSpace(low_freq=100, high_freq=44100 / 2, n=8)[::-1]).astype(
    #     int
    # )

    def _plot_subbands(ax, times, signal):
        N = signal.shape[0]

        for n, sig in enumerate(np.flip(signal, axis=0)):
            ax.plot(times, sig + n, color="k", linewidth=0.3)

        ax.set_yticks(np.arange(N), labels=np.arange(N))
        ax.set_xticks([0.0, 0.05, 0.1], labels=[0, 50, 100])
        ax.set_xlabel("Time (ms)")

    fig, ax = plt.subplots(1, 3, figsize=figsize, sharey=True, layout="constrained")
    X = audio.times
    _plot_subbands(ax[0], X, subbands)
    _plot_subbands(ax[1], X, envelope)
    ax[2].imshow(coch, aspect="auto", extent=(0, 100, -0.5, 7.5), cmap="magma")
    ax[2].set_yticks(np.arange(8), np.arange(8))

    ax[0].set_title("Audio sub-bands", fontsize=plt.rcParams["axes.labelsize"])
    ax[0].set_ylabel("Frequency (Hz)")
    ax[0].set_yticklabels(
        ["100", "320", "715", "1.4k", "2.5k", "4.4k", "7.5k", "12.9k"]
    )
    ax[1].set_title("Envelopes", fontsize=plt.rcParams["axes.labelsize"])
    ax[2].set_title("Cochleagram", fontsize=plt.rcParams["axes.labelsize"])

    for a in ax:
        a.set_xlabel("Time (ms)")
        a.set_ylim((-0.5, 8))

    ax[2].set_facecolor("black")

    fig.savefig(output_dir / "cochleagram_steps.pdf")


@app.command()
def draw_adress(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_RECT,
    sr=44100,
    fft_size=128,
    hop_size=64,
    gain=0.1,
):
    partials_a = np.fft.rfftfreq(fft_size, d=1 / sr)[[11, 21, 31, 41]]
    partials_b = np.fft.rfftfreq(fft_size, d=1 / sr)[[15, 25, 35, 45]]
    a = sum(
        [pf.signals.sine(f, sr, sampling_rate=sr, amplitude=gain) for f in partials_a]
    )
    b = sum(
        [pf.signals.sine(f, sr, sampling_rate=sr, amplitude=gain) for f in partials_b]
    )

    a = a * [1, 0.4]
    b = b * [0.4, 1]
    mix = a + b

    spect = np.abs(common.make_spectrogram(mix, fft_size=fft_size, hop_size=hop_size))
    faas = sarroff.frequency_azimuth_analysis_signal(spect, 100, inverted=False)
    fap = np.mean(faas, axis=0)
    nulls_x = [np.argmin(fap[41]), np.argmin(fap[45])]
    freqs = np.fft.rfftfreq(fft_size, d=1 / sr)

    fig, ax = plt.subplots(1, 1, figsize=figsize, layout="constrained")
    img = ax.imshow(
        np.flipud(fap),
        aspect="auto",
        cmap="gray_r",
        extent=(0, fap.shape[1], 0, sr / 2),
    )
    ax.set_yticks(
        [0, 5000, 10000, 15000, 20000], labels=["0", "5k", "10k", "15k", "20k"]
    )
    ax.vlines(nulls_x, ymin=0, ymax=sr / 2, color="red", linestyle="dashed")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Azimuth")
    ax.set_xticks([0, 100, 200], ["L", "C", "R"])

    freqs = np.fft.rfftfreq(fft_size, d=1 / sr)
    arrowprops = dict(arrowstyle="->")
    bbox = dict(boxstyle="ellipse", alpha=0.0)
    for i in [11, 21, 31, 41]:
        null_y = freqs[i]
        ax.annotate(
            "nulls",
            (nulls_x[0], null_y),
            (100, 18000),
            xycoords="data",
            arrowprops=arrowprops,
            ha="center",
            bbox=bbox,
        )
    for i in [15, 25, 35, 45]:
        null_y = freqs[i]
        ax.annotate(
            "nulls",
            (nulls_x[1], null_y),
            (100, 18000),
            xycoords="data",
            arrowprops=arrowprops,
            ha="center",
            bbox=bbox,
        )

    fig.savefig(output_dir / "adress.pdf")


@app.command()
def draw_adress_frames_for_track(
    output_dir: Path = OUTPUT_DIR,
    track_idx: int = 2,
    fft_size=128,
    hop_size=64,
    start_frame=700,
    num_frames=8,
    frame_skip=1,
):
    track_filepath = get_demo_tracks().iloc[track_idx].local.filepath
    mix = pf.io.read_audio(track_filepath)

    spect = np.abs(common.make_spectrogram(mix, fft_size=fft_size, hop_size=hop_size))
    faas = sarroff.frequency_azimuth_analysis_signal(spect, 100, inverted=False)

    cmap = plt.cm.gray_r
    frame_selection = faas[start_frame : start_frame + num_frames : frame_skip]
    for i, fap in enumerate(frame_selection):
        norm = plt.Normalize(vmin=fap.min(), vmax=fap.max())
        image = cmap(norm(np.flipud(fap)))
        plt.imsave(output_dir / f"fa_{i:05d}.png", image)


@app.command()
def make_demo_tracks_appendix_table(output_dir: Path = OUTPUT_DIR):
    tracks = get_demo_tracks()
    appendix_table = pd.DataFrame(
        {
            "Track ID": tracks.index.values,
            "Artist": tracks.artist.name.values,
            "Title": tracks.track.title.values,
            "Genres": tracks.track.genres.map(lambda l: ", ".join(l)).values,
            "Letter": tracks.local.letter.values,
        }
    )
    appendix_table.to_latex(output_dir / "demo_tracks.tex", index=False)


@app.command()
def make_freesound_appendix_table(output_dir: Path = OUTPUT_DIR):
    tracks = get_freesound_clips()

    def _latex_url(url: str) -> str:
        return f"\\url{{{url}}}"

    appendix_table = pd.DataFrame(
        {
            "Sound ID": tracks.index.values,
            "Name": tracks.name.values,
            "URL": tracks.url.map(_latex_url),
        }
    )
    appendix_table.to_latex(output_dir / "freesounds.tex", index=False)


@app.command()
def draw_demo_tracks_spf(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_RECT,
):
    tracks = get_demo_tracks()
    fig, axes = plt.subplots(1, 3, figsize=figsize, sharey=True, layout="constrained")
    for (_idx, track), ax in zip(tracks.iterrows(), axes):
        audio = pf.io.read_audio(track.local.filepath)
        spect = common.make_spectrogram(audio)
        spf = tzanetakis.stereo_panning_features(spect, audio.sampling_rate, 40)
        display.display_spf(
            spf,
            f"{track.local.letter}",
            ax,
            ylim=dict(bottom=-0.1, top=6.7),
            xlim=dict(left=0.0, right=4.0),
        )
    axes[0].set_ylabel("Feature value")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles=handles, labels=labels, loc="outside upper center", ncols=2)

    fig.savefig(output_dir / "spf.pdf")


@app.command()
def draw_demo_tracks_ph(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_RECT,
):
    tracks = get_demo_tracks()
    fig, axes = plt.subplots(1, 3, figsize=figsize, layout="constrained")
    for (_idx, track), ax in zip(tracks.iterrows(), axes):
        audio = pf.io.read_audio(track.local.filepath)
        spect = common.make_spectrogram(audio)
        ph_gomez = gomez.panning_histogram(spect, 65)
        ph_sarroff = sarroff.panning_histogram(np.abs(spect), 32)
        ph_sarroff /= np.sum(ph_sarroff)
        ymax = np.max([ph_sarroff, ph_gomez])
        ylim = (ymax * -0.1, ymax * 1.1)
        display.draw_panning_histogram(
            ph_gomez,
            ax,
            track.local.letter,
            ylim,
            color="k",
            linestyle="--",
            label="Gomez",
            linewidth=0.618,
        )
        display.draw_panning_histogram(
            ph_sarroff,
            ax,
            track.local.letter,
            ylim,
            color="k",
            linestyle="-",
            label="Sarroff",
            linewidth=0.618,
        )

    for ax in axes[1:3]:
        ax.set_ylabel(None)

    for ax in axes:
        ax.get_legend().remove()

    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(
        handles=handles,
        labels=labels,
        loc="outside upper center",
        fancybox=True,
        shadow=False,
        ncol=2,
    )

    fig.savefig(output_dir / "panning_histograms.pdf")


@app.command()
def draw_demo_tracks_asf(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_RECT,
):
    tracks = get_demo_tracks()

    @cache_to_disk(99)
    def _make_asf(filepath):
        audio = pf.io.read_audio(filepath)
        coch = tardieu.cochleagram(audio, 0.04, 0.02, 70)
        return tardieu.amplitude_stereo_features(coch)

    fig, axes = plt.subplots(1, 3, figsize=figsize, sharey=True, layout="constrained")
    for (_idx, track), ax in zip(tracks.iterrows(), axes):
        asf = _make_asf(track.local.filepath)
        freqs = pat.ErbSpace(low_freq=30, high_freq=44100 / 2, n=70)[::-1]
        ax.errorbar(
            asf.mean_over_time,
            freqs,
            xerr=asf.std_over_time,
            marker="o",
            linestyle="none",
            color="k",
            linewidth=0.5,
            markersize=2,
        )
        ax.set_yscale("log")
        ax.set_ylim(20, 30000)
        ax.set_xlim(-0.11, 0.11)
        ax.set_xlabel("Panning amount")
        ax.set_title(track.local.letter)
    axes[0].set_ylabel("Frequency (Hz)")
    fig.savefig(output_dir / "asf.pdf")


# Look below for the app command
def _draw_harma(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_SQUARE,
):
    # 1. Define grid parameters for the smooth surface mesh
    N = 100
    theta_steps = np.linspace(np.pi / 2, 0, N + 1)
    phi_steps = np.linspace(0, np.pi / 2, N + 1)
    THETA, PHI = np.meshgrid(theta_steps, phi_steps)

    # 2. Map surface to Cartesian coordinates
    X = np.sin(THETA) * np.cos(PHI)
    Y = np.sin(THETA) * np.sin(PHI)
    Z = np.cos(THETA)

    # 3. Define the true symmetric Surface Center Point in polar coordinates
    c_val = 1.0 / np.sqrt(3)  # Coordinates where X = Y = Z
    t_center = np.arccos(c_val)
    p_center = np.pi / 4

    # 4. Define the buffer distance from the corners
    chord_dist = 0.25
    offset = 1.006  # Floats lines slightly above the surface mesh
    sweep_res = 50

    # 5. FIX: Calculate exact polar stopping coordinates to precisely hit the arcs
    # --- Z-Corner intercept logic
    z_stop_val = 1.0 - (chord_dist**2 / 2.0)
    t_stop_z = np.arccos(z_stop_val)
    p_stop_z = np.pi / 4

    # --- X-Corner intercept logic (where X meets the chord distance, and Y=Z by symmetry)
    x_stop_val = 1.0 - (chord_dist**2 / 2.0)
    yz_stop_val = np.sqrt((1.0 - x_stop_val**2) / 2.0)
    t_stop_x = np.arccos(yz_stop_val)
    p_stop_x = np.arctan2(yz_stop_val, x_stop_val)

    # --- Y-Corner intercept logic (where Y meets the chord distance, and X=Z by symmetry)
    y_stop_val = 1.0 - (chord_dist**2 / 2.0)
    xz_stop_val = np.sqrt((1.0 - y_stop_val**2) / 2.0)
    t_stop_y = np.arccos(xz_stop_val)
    p_stop_y = np.arctan2(y_stop_val, xz_stop_val)

    # 6. FIX: Revert main paths to pure polar linear interpolation (Great-Circle tracks)
    def polar_to_cart(t, p, r_offset=1.006):
        """
        Transforms 3D spherical polar coordinates into Cartesian coordinates
        for a sphere of unit radius (R=1).

        Parameters:
        -----------
        t : float or numpy.ndarray
            Theta (polar angle / colatitude) in radians. Represents the angular
            displacement down from the positive Z-axis [0, pi].
        p : float or numpy.ndarray
            Phi (azimuthal angle) in radians. Represents the angular rotation
            counter-clockwise from the positive X-axis in the XY plane [0, 2*pi].
        r_offset : float, optional
            A fractional multiplier applied to the base unit radius (R=1).
            Defaults to 1.006. This scales the vector out slightly to prevent
            3D rendering artifacts ("Z-fighting") when plotting lines directly
            on top of a pre-rendered surface mesh.

        Returns:
        --------
        tuple of (float or numpy.ndarray)
            A 3-element tuple containing the mapped (X, Y, Z) Cartesian coordinates.
            Matches the dimension and shape of the input array arrays.
        """
        x = np.sin(t) * np.cos(p) * r_offset
        y = np.sin(t) * np.sin(p) * r_offset
        z = np.cos(t) * r_offset
        return x, y, z

    def draw_text_on_surface(ax, text, t, p, text_offset=1.05, **kwargs):
        """
        Plots text labels directly onto the 3D surface of the sphere using polar coordinates.

        Parameters:
        -----------
        ax : matplotlib.axes._subplots.Axes3DSubplot
            The active 3D plot axis object.
        text : str
            The text string to display.
        t : float
            Theta (polar angle / colatitude) in radians.
        p : float
            Phi (azimuthal angle) in radians.
        text_offset : float, optional
            The radial scaling factor to float the text cleanly above the surface
            and prevent it from clipping through the 3D mesh. Defaults to 1.05.
        **kwargs : dict, optional
            Standard matplotlib text properties (e.g., color, fontsize, fontweight,
            horizontalalignment).

        Returns:
        --------
        matplotlib.text.Text3D
            The created 3D text object.
        """
        # Convert polar angles to 3D Cartesian space with a safe text offset
        x, y, z = polar_to_cart(t, p, r_offset=text_offset)

        # Set default clean alignments if they aren't explicitly provided
        kwargs.setdefault("horizontalalignment", "center")
        kwargs.setdefault("verticalalignment", "center")
        kwargs.setdefault("color", "black")

        # Render text onto the 3D axes
        return ax.text(x, y, z, text, **kwargs)

    # Interpolate angles linearly and convert to 3D paths
    x_main = polar_to_cart(
        np.linspace(t_center, t_stop_x, 50), np.linspace(p_center, p_stop_x, 50), offset
    )
    y_main = polar_to_cart(
        np.linspace(t_center, t_stop_y, 50), np.linspace(p_center, p_stop_y, 50), offset
    )
    z_main = polar_to_cart(
        np.linspace(t_center, t_stop_z, 50), np.linspace(p_center, p_stop_z, 50), offset
    )

    # 7. Keep the distance-based boundary arcs from scratch
    sweep = np.linspace(0, np.pi / 2, sweep_res)

    # --- Z-Corner Arc (Constant distance from (0,0,1))
    z_arc_z = np.full_like(sweep, z_stop_val)
    r_xy_z = np.sqrt(1.0 - z_arc_z**2)
    z_b = polar_to_cart(np.arccos(z_arc_z), sweep, offset)

    # --- X-Corner Arc (Constant distance from (1,0,0))
    x_arc_x = np.full_like(sweep, x_stop_val)
    r_yz_x = np.sqrt(1.0 - x_arc_x**2)
    x_b = np.array([x_arc_x, r_yz_x * np.cos(sweep), r_yz_x * np.sin(sweep)]) * offset

    # --- Y-Corner Arc (Constant distance from (0,1,0))
    y_arc_y = np.full_like(sweep, y_stop_val)
    r_xz_y = np.sqrt(1.0 - y_arc_y**2)
    y_b = np.array([r_xz_y * np.cos(sweep), y_arc_y, r_xz_y * np.sin(sweep)]) * offset

    # 8. Plot setup
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    # Smooth surface shading
    light = LightSource(azdeg=315, altdeg=45)
    rgb = light.shade(Z, cmap=plt.get_cmap("grey"), blend_mode="soft")
    ax.plot_surface(
        X,
        Y,
        Z,
        facecolors=rgb,
        edgecolor="none",
        linewidth=0,
        antialiased=False,
        shade=False,
    )

    # Plot Surface-Hugging Main Paths (Black)
    ax.plot(*x_main, color="red", linewidth=2, zorder=5)
    ax.plot(*y_main, color="red", linewidth=2, zorder=5)
    ax.plot(*z_main, color="red", linewidth=2, zorder=5)

    # Plot Distance-Perfect Boundary Lines (Crimson Red)
    ax.plot(*x_b, color="red", linewidth=2, zorder=6)
    ax.plot(*y_b, color="red", linewidth=2, zorder=6)
    ax.plot(*z_b, color="red", linewidth=2, zorder=6)

    # Highlight Center Point
    # ax.scatter(*polar_to_cart(t_center, p_center, offset), color='cyan', s=100, zorder=7)

    draw_text_on_surface(ax, "I", 1.45, 0.2, color="white", zorder=10)
    draw_text_on_surface(ax, "II", np.pi / 4, 0.5, color="black", zorder=10)
    draw_text_on_surface(
        ax, "III", np.pi / 4, np.pi / 2 - 0.5, color="black", zorder=10
    )
    draw_text_on_surface(
        ax, "IV", np.pi / 2 - 0.35, np.pi / 4, color="white", zorder=10
    )
    draw_text_on_surface(
        ax, "V", np.pi / 2 - 0.1, np.pi / 2 - 0.1, color="white", zorder=10
    )
    draw_text_on_surface(ax, "VI", 0.2, np.pi / 4 + 0.2, color="black", zorder=10)

    # Visual styling
    ax.set_ylabel(r"variance $\sigma_p$")
    ax.set_xlabel(r"variance $\sigma_s$")
    ax.set_zlabel(r"variance $\sigma_{uv}$")
    ax.set_xlim(0, 1.1)
    ax.set_ylim(0, 1.1)
    ax.set_zlim(0, 1.1)
    ax.view_init(elev=15, azim=60)

    fig.savefig(output_dir / "harma.pdf")


@app.command()
def draw_harma(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_SQUARE,
):
    # Use TeX to get nice sigma symbols
    with plt.rc_context(plt.rcParams | {"text.usetex": True}):
        _draw_harma(output_dir, figsize)


@app.command()
def draw_demo_tracks_goniometer(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_RECT,
):
    tracks = get_demo_tracks()
    fig, axes = plt.subplots(2, 3, figsize=figsize, sharex=True, layout="constrained")

    for col_idx, (_idx, track) in enumerate(tracks.iterrows()):
        audio = pf.io.read_audio(track.local.filepath)
        box, corr = ziemer.feature_vectors(audio, 0.04, 0.04)
        t = np.arange(len(box)) * 0.04
        axes[0, col_idx].plot(t, box, color="k", linewidth=0.3)
        axes[1, col_idx].plot(t, corr, color="k", linewidth=0.3)
        axes[0, col_idx].set_ylim(-0.03, 0.43)
        axes[1, col_idx].set_ylim(-1.1, 1.1)
        axes[1, col_idx].set_xlabel("Time (s)")
        axes[1, col_idx].set_xticks([0, 10, 20, 30])
        axes[0, col_idx].set_title(track.local.letter)

    axes[0, 0].set_ylabel("Normalized\nbox count")
    axes[1, 0].set_ylabel("Channel\ncorrelation")
    axes[0, 1].set_yticklabels([])
    axes[0, 2].set_yticklabels([])
    axes[1, 1].set_yticklabels([])
    axes[1, 2].set_yticklabels([])

    fig.savefig(output_dir / "goniometer_features.pdf")


@app.command()
def draw_example_goniometer(
    output_dir: Path = OUTPUT_DIR,
    track_idx: int = 1,
    start: float = 19.48,
    duration: float = 0.04,
    # It's important that the two graphs in this figure end up being square,
    # so use a custom figsize.
    figsize: Tuple[float, float] = (LATEX_LINEWIDTH, LATEX_LINEWIDTH * 0.47),
):

    from numpy import pi

    filename = get_demo_tracks().iloc[track_idx].local.filepath

    def _colored_line(x, y, c, ax=None, **lc_kwargs):
        """
        Plot a line with a color specified along the line by a third value.

        It does this by creating a collection of line segments. Each line segment is
        made up of two straight lines each connecting the current (x, y) point to the
        midpoints of the lines connecting the current point with its two neighbors.
        This creates a smooth line with no gaps between the line segments.

        Parameters
        ----------
        x, y : array-like
            The horizontal and vertical coordinates of the data points.
        c : array-like
            The color values, which should be the same size as x and y.
        ax : matplotlib.axes.Axes, optional
            The axes to plot on. If not provided, the current axes will be used.
        **lc_kwargs
            Any additional arguments to pass to matplotlib.collections.LineCollection
            constructor. This should not include the array keyword argument because
            that is set to the color argument. If provided, it will be overridden.

        Returns
        -------
        matplotlib.collections.LineCollection
            The generated line collection representing the colored line.
        """

        xy = np.stack((x, y), axis=-1)
        xy_mid = np.concat(
            (xy[0, :][None, :], (xy[:-1, :] + xy[1:, :]) / 2, xy[-1, :][None, :]),
            axis=0,
        )
        segments = np.stack((xy_mid[:-1, :], xy, xy_mid[1:, :]), axis=-2)
        # Note that
        # segments[0, :, :] is [xy[0, :], xy[0, :], (xy[0, :] + xy[1, :]) / 2]
        # segments[i, :, :] is [(xy[i - 1, :] + xy[i, :]) / 2, xy[i, :],
        #     (xy[i, :] + xy[i + 1, :]) / 2] if i not in {0, len(x) - 1}
        # segments[-1, :, :] is [(xy[-2, :] + xy[-1, :]) / 2, xy[-1, :], xy[-1, :]]

        # lc_kwargs["array"] = c
        lc_kwargs["alpha"] = c
        lc = LineCollection(segments, **lc_kwargs)

        # Plot the line collection to the axes
        ax = ax or plt.gca()
        ax.add_collection(lc)

        return lc

    def _rotate_matrix(x, y, angle, x_shift=0, y_shift=0, units="DEGREES"):
        """
        Rotates a point in the xy-plane counterclockwise through an angle about the origin
        https://en.wikipedia.org/wiki/Rotation_matrix
        :param x: x coordinate
        :param y: y coordinate
        :param x_shift: x-axis shift from origin (0, 0)
        :param y_shift: y-axis shift from origin (0, 0)
        :param angle: The rotation angle in degrees
        :param units: DEGREES (default) or RADIANS
        :return: Tuple of rotated x and y
        """

        # Shift to origin (0,0)
        x = x - x_shift
        y = y - y_shift

        # Convert degrees to radians
        if units == "DEGREES":
            angle = math.radians(angle)

        # Rotation matrix multiplication to get rotated x & y
        xr = (x * math.cos(angle)) - (y * math.sin(angle)) + x_shift
        yr = (x * math.sin(angle)) + (y * math.cos(angle)) + y_shift

        return xr, yr

    # main figure
    fig, ax = plt.subplots(1, 2, figsize=figsize, layout="constrained")
    audio = pf.dsp.time_crop(
        pf.io.read_audio(filename), [start, start + duration], unit="s"
    )
    x, y = _rotate_matrix(audio.time[0], audio.time[1], 45)

    # draw shaded line
    c = np.linspace(0, 1, audio.n_samples)
    _colored_line(x, y, c, ax=ax[0], color="k", linewidth=0.5)
    ax[0].set_xlim(-1, 1)
    ax[0].set_ylim(-1, 1)

    # draw unit circle
    for r in [0.25, 0.5, 0.75, 1]:
        M = 100
        xc = np.cos(np.linspace(0, 2 * np.pi, M)) * r
        yc = np.sin(np.linspace(0, 2 * np.pi, M)) * r
        ax[0].plot(xc, yc, color="grey", alpha=0.5, linewidth=0.5, linestyle="dotted")

    # Draw left, centre, and right markers
    line_lx, line_ly = common.polar_to_cartesian(1, [-pi / 4, 3 * pi / 4])
    line_cx, line_cy = common.polar_to_cartesian(1, [-pi / 2, -3 * pi / 2])
    line_rx, line_ry = common.polar_to_cartesian(1, [pi / 4, -3 * pi / 4])
    ax[0].plot(
        line_lx, line_ly, color="grey", alpha=0.5, linewidth=0.5, linestyle="dotted"
    )
    ax[0].plot(
        line_cx, line_cy, color="grey", alpha=0.5, linewidth=0.5, linestyle="dotted"
    )
    ax[0].plot(
        line_rx, line_ry, color="grey", alpha=0.5, linewidth=0.5, linestyle="dotted"
    )

    text_rx, text_ry = common.polar_to_cartesian(1.1, pi / 4)
    text_cx, text_cy = common.polar_to_cartesian(0.9, pi / 2 + 0.1)
    text_lx, text_ly = common.polar_to_cartesian(1.1, 3 * pi / 4)
    ax[0].text(
        text_rx,
        text_ry,
        "R",
        horizontalalignment="center",
        verticalalignment="center",
        transform=ax[0].transData,
        color="grey",
    )
    ax[0].text(
        text_cx,
        text_cy,
        "C",
        horizontalalignment="center",
        verticalalignment="center",
        transform=ax[0].transData,
        color="grey",
    )
    ax[0].text(
        text_lx,
        text_ly,
        "L",
        horizontalalignment="center",
        verticalalignment="center",
        transform=ax[0].transData,
        color="grey",
    )

    # Box diagram
    N = 10
    xq = (x * N).astype(int) + N
    yq = (y * N).astype(int) + N
    grid = np.zeros((2 * N, 2 * N))
    for xx, yy in np.stack([xq, yq]).T:
        grid[xx, yy] += 1
    unique_boxes = np.sum(grid != 0)
    total_boxes = int((2 * N) ** 2)
    grid[grid == 0] = np.nan
    cmap = plt.cm.plasma
    cmap.set_bad("black", 1.0)
    img = ax[1].imshow(np.fliplr(grid), aspect="auto", cmap=cmap)

    # gridlines
    ax[1].hlines(
        np.arange(2 * N - 1) + 0.5,
        xmin=-0.5,
        xmax=19.5,
        color="white",
        alpha=0.5,
        linewidth=0.5,
    )
    ax[1].vlines(
        np.arange(2 * N - 1) + 0.5,
        ymin=-0.5,
        ymax=19.5,
        color="white",
        alpha=0.5,
        linewidth=0.5,
    )

    # anotation
    ax[1].text(
        0.05,
        0.90,
        f"Unique boxes = {unique_boxes}/{total_boxes}",
        color="white",
        bbox=dict(facecolor="black", edgecolor="white"),
        transform=ax[1].transAxes,
    )

    # ticks and labels
    ax[0].set_xticks([])
    ax[1].set_xticks([])
    ax[0].set_yticks([])
    ax[1].set_yticks([])
    ax[0].set_title("Goniometer")
    ax[1].set_title("Boxes")

    cbar = fig.colorbar(img)
    cbar.set_label("Number of samples in box")

    fig.savefig(output_dir / "goniometer.pdf")


@app.command()
def draw_pi_and_ai(
    output_dir: Path = OUTPUT_DIR,
    track_idx: int = 2,
    figsize: Tuple[float, float] = WIDE_SQUARE,
):
    filepath = get_demo_tracks().iloc[track_idx].local.filepath
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True, layout="constrained")
    sig = pf.io.read_audio(filepath)
    spect = common.make_spectrogram(sig)
    freqs = np.fft.rfftfreq(1024, d=1 / sig.sampling_rate)[1:]
    pi = avendano.panning_index(spect)[:, 1:]
    ai = avendano.ambiance_index(spect)[:, 1:]

    extent = [0, sig.times[-1], 0, freqs[-1]]
    img_pi = axes[0].imshow(
        np.rot90(pi),
        aspect="auto",
        cmap="berlin",
        extent=extent,
        # norm=SymLogNorm(0.1, vmin=-1, vmax=1)
    )
    img_ai = axes[1].imshow(np.rot90(ai), aspect="auto", cmap="grey", extent=extent)

    for ax in axes:
        ax.set_yscale("log")
        ax.set_ylim(50, 20000)
        ax.set_ylabel("Frequency (Hz)")
        ax.set_yticks([100, 1000, 10000], labels=["100", "1k", "10k"])
    axes[1].set_xlabel("Time (s)")

    tx, ty = 0.03, 0.95
    axes[0].text(
        tx,
        ty,
        "Panning Index",
        transform=axes[0].transAxes,
        verticalalignment="top",
        bbox=ANNOTATION_BBOX_PROPS,
    )
    axes[1].text(
        tx,
        ty,
        "Ambience Index",
        transform=axes[1].transAxes,
        verticalalignment="top",
        bbox=ANNOTATION_BBOX_PROPS,
    )

    cbar_pi = fig.colorbar(img_pi, ax=axes[0])
    cbar_pi.set_ticks([-1, 0, 1], labels=["Left", "Centre", "Right"])
    cbar_ai = fig.colorbar(img_ai, ax=axes[1])
    cbar_ai.set_ticks([0, 1])

    fig.savefig(output_dir / "pi_ai.pdf")


@app.command()
def make_page(img_dir: Path = OUTPUT_DIR):
    ltx = r"""
    \documentclass[preview]{standalone}
    \usepackage{graphicx}
    \setlength{\fboxsep}{0pt}
    \setlength{\fboxrule}{1pt}
    \begin{document}
    IMGS
    \end{document}
    """

    imgs_str = ""
    for img in img_dir.glob("*.pdf"):
        imgs_str += f"\\fbox{{\includegraphics{{{img}}}\n\\vspace{{1cm}}}}\n\n"

    ltx = ltx.replace("IMGS", imgs_str)

    ltx = "\n".join([l.strip() for l in ltx.splitlines()])

    print(ltx)

    subprocess.run(["tectonic", "-"], input=ltx.encode())


@app.command()
def all(output_dir: Path = OUTPUT_DIR):
    make_freesound_appendix_table(output_dir)
    make_brir_dats(output_dir)
    make_ild_itd_dats(output_dir)
    draw_panned_drums(output_dir)
    draw_nyquist(output_dir)
    draw_equal_power_panning(output_dir)
    draw_spectrogram_comparison(output_dir)
    draw_gammatone_filters(output_dir)
    draw_mel_filters(output_dir)
    draw_cochleagram_steps(output_dir)
    draw_adress(output_dir)
    draw_adress_frames_for_track(output_dir)
    make_demo_tracks_appendix_table(output_dir)
    draw_demo_tracks_spf(output_dir)
    draw_demo_tracks_ph(output_dir)
    draw_demo_tracks_asf(output_dir)
    draw_demo_tracks_goniometer(output_dir)
    draw_pi_and_ai(output_dir)
    draw_example_goniometer(output_dir)
    draw_harma(output_dir)
    make_page(output_dir)


# just to get both diagrams in one command
@app.command()
def adress(
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = WIDE_RECT,
):
    draw_adress(output_dir, figsize)
    draw_adress_frames_for_track(output_dir, 2)

# all the generated dat files
@app.command()
def dats(
    output_dir: Path = OUTPUT_DIR,
):
    make_brir_dats(output_dir)
    make_ild_itd_dats(output_dir)



if __name__ == "__main__":
    app()
