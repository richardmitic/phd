from openpyxl.styles.builtins import total
import seaborn
import re
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
from typing import List, Tuple, Any, Optional

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

# Main app. Smaller functions can be called as individual comamnds
app = typer.Typer(result_callback=_maybe_print)

# default matplotlib style
plt.rcParams["font.family"] = "Times"
plt.rcParams["font.size"] = 9

# Default parameters
OUTPUT_DIR = _git_root() / "papers/licentiate_presentation/generated"

@app.command()
def draw_phs(
    input_files: List[Path],
    xy_range: Tuple[int, int] = (6,5),
    figsize: Tuple[float, float] = (12.8, 7.2),
    output_path: Optional[Path] = None,
    legend: bool = True,
):
    ncols, nrows = xy_range
    fig, axes = plt.subplots(
        nrows, ncols, 
        sharex=True, 
        sharey=False, 
        layout='constrained',
        figsize = figsize,
    )
    axes = np.atleast_1d(axes)

    for file, ax in zip(input_files, axes.flat):
        print(file)
        audio = common.read_audio(file, start=30, duration=30)
        spect = common.make_spectrogram(audio)
        ph_gomez = gomez.panning_histogram(spect, 65)
        ph_sarroff = sarroff.panning_histogram(np.abs(spect), 32)
        ph_sarroff /= np.sum(ph_sarroff)
        ymax = np.max(np.concat([ph_sarroff, ph_gomez]))
        ylim = (ymax * -0.1, ymax * 1.1)

        display.draw_panning_histogram(
            ph_gomez,
            ax,
            "",
            ylim,
            grid=True,
            quartiles=True,
            plot_kwargs=dict(
                color="#FFC20A",
                label="Gomez",
            ),
            x_label=None,
            y_label=None,
            legend=False,
        )
        display.draw_panning_histogram(
            ph_sarroff,
            ax,
            "",
            ylim,
            quartiles=True,
            plot_kwargs=dict(
                color="#0C7BDC",
                label="Sarroff",
            ),
            x_label=None,
            y_label=None,
            legend=legend,
        )

    if output_path:
        fig.savefig(output_path)
    else:
        plt.show()

@app.command()
def draw_gonios(
    input_files: List[Path],
    xy_range: Tuple[int, int] = (6,5),
    fig_width: float = 12.8,
    output_path: Optional[Path] = None,
):
    ncols, nrows = xy_range

    # Goniometers must be cicular so calculate the figure size from width
    fig_height = (fig_width / ncols) * nrows

    print(fig_width, fig_height)

    fig, axes = plt.subplots(
        nrows, ncols, 
        sharex=True, 
        sharey=True, 
        layout='constrained',
        figsize = (fig_width, fig_height),
    )
    for file, ax in zip(input_files, axes.flat):
        print(file)
        audio = common.read_audio(file, start=30, duration=0.05)
        display.draw_goniometer(audio, ax)

    if output_path:
        fig.savefig(output_path)
    else:
        plt.show()

@app.command()
def draw_spfs(
    input_files: List[Path],
    xy_range: Tuple[int, int] = (8,6),
    figsize: Tuple[float, float] = (12.8, 7.2),
    output_path: Optional[Path] = None,
):
    ncols, nrows = xy_range
    fig, axes = plt.subplots(
        nrows, ncols, 
        sharex=True, 
        sharey=True, 
        layout='constrained',
        figsize = figsize,
    )
    for file, ax in zip(input_files, axes.flat):
        print(file)
        audio = common.read_audio(file, start=30, duration=30)
        spect = common.make_spectrogram(audio)
        spf = tzanetakis.stereo_panning_features(spect, audio.sampling_rate, 40)
        display.display_spf(spf, "", ax, ylim={"bottom": -0.1, "top": 5}, xlabel=None)

    for ax in axes[-1]:
        ax.set_xlabel("Frequency band")
    
    for ax in axes[:,0]:
        ax.set_ylabel("Feature value")
    
    if output_path:
        fig.savefig(output_path)
    else:
        plt.show()


@app.command()
def draw_asfs(
    input_files: List[Path],
    xy_range: Tuple[int, int] = (5,3),
    figsize: Tuple[float, float] = (12.8, 7.2),
    output_path: Optional[Path] = None,
):
    from python_auditory_toolbox import auditory_toolbox as pat
    from cache_to_disk import cache_to_disk
    
    ncols, nrows = xy_range
    fig, axes = plt.subplots(
        nrows, ncols, 
        sharex=True, 
        sharey=True, 
        layout='constrained',
        figsize = figsize,
    )

    # calculating ASF is really slow so cache the results
    @cache_to_disk()
    def _get_asf(file: Path):
        audio = common.read_audio(file, start=30, duration=30)
        coch = tardieu.cochleagram(audio, 0.2, 0.1, 70)
        return tardieu.amplitude_stereo_features(coch) 

    for file, ax, in zip(input_files, axes.flat):
        print(file)
        asf = _get_asf(file)
        freqs = pat.ErbSpace(low_freq=30, high_freq=44100/2, n=70)
        display.display_asf(asf, ax, freqs, 0.05)
    
    for ax in axes[:,0]:
        ax.set_ylabel("Frequency (Hz)")

    for ax in axes[-1]:
        ax.set_xlabel("Panning amount")

    if output_path:
        fig.savefig(output_path)
    else:
        plt.show()

@app.command()
def tile(
    input_files: List[Path],
    xy_range: Tuple[int, int] = (2,2),
    root: Path = _git_root() / "papers/licentiate_presentation",
    ratio: float = 3/4,
):
    from itertools import product
    tex = r'\begin{tikzpicture}'

    coords = product(range(xy_range[0]), range(xy_range[1]))

    for (x, y), file in zip(coords, input_files):
        f = file.resolve().relative_to(root)
        tex += "\n"
        tex += f"\\node at ({x}, {y*ratio}) {{\\includegraphics[width=1cm]{{{f}}}}};"
    tex += '\n\\end{tikzpicture}'
    print(tex)

@app.command()
def cost_graph(
    file: Path,
    output_path: Optional[Path] = None,
):
    from matplotlib.dates import ConciseDateFormatter

    df = pd.read_csv(file)
    df.date = pd.to_datetime(df.date)
    fig, ax = plt.subplots(figsize=(4,2.5), layout='constrained')

    sp_green = "#60d36d"
    sp_blue = "#adeee0"
    idle_cost = df.cost.loc[df.cost < 2].sum()
    total_cost = df.cost.sum()
    processing_cost = total_cost - idle_cost
    ax.bar(df.date[df.cost>=2], df.cost[df.cost>=2], color=sp_green, label=f"Processing: ${processing_cost:.2f}")
    ax.bar(df.date[df.cost<2], df.cost[df.cost<2], color=sp_blue, label=f"Idle: ${idle_cost:.2f}")
    ax.set_ylabel("Cost (USD)")
    ax.xaxis.set_major_formatter(ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.set_xlabel("Date")
    ax.legend()

    if output_path is not None:
        fig.savefig(output_path)
    else:
        plt.show()

@app.command()
def hello():
    return _git_root()

if __name__ == "__main__":
    app()
