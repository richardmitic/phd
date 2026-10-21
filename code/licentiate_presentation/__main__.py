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
from typing import List, Tuple, Any

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
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = (4, 3),
):
    _ensure_dir(output_dir)
    for file in input_files:
        print(file)
        fig, ax = plt.subplots(figsize=figsize, layout="constrained")
        audio = common.read_audio(file, start=30, duration=30)
        spect = common.make_spectrogram(audio)
        ph_gomez = gomez.panning_histogram(spect, 65)
        ph_sarroff = sarroff.panning_histogram(np.abs(spect), 32)
        ph_sarroff /= np.sum(ph_sarroff)
        ymax = np.max([ph_sarroff, ph_gomez])
        ylim = (ymax * -0.1, ymax * 1.1)

        display.draw_panning_histogram(
            ph_gomez,
            ax,
            "",
            ylim,
            grid=True,
            quartiles=True,
            color="#FFC20A",  # type: ignore
            label="Gomez",  # type: ignore
        )
        display.draw_panning_histogram(
            ph_sarroff,
            ax,
            "",
            ylim,
            quartiles=True,
            color="#0C7BDC",  # type: ignore
            label="Sarroff",  # type: ignore
        )

        fig.savefig(output_dir / f"{file.stem}.pdf")
        plt.close()

@app.command()
def draw_gonios(
    input_files: List[Path],
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = (3,3*0.94),
):
    _ensure_dir(output_dir)
    for file in input_files:
        print(file)
        fig, ax = plt.subplots(figsize=figsize, layout="constrained")
        audio = common.read_audio(file, start=30, duration=0.05)
        display.draw_goniometer(audio, ax)
        fig.savefig(output_dir / f"{file.stem}.pdf")
        plt.close()

@app.command()
def draw_spfs(
    input_files: List[Path],
    output_dir: Path = OUTPUT_DIR,
    figsize: Tuple[float, float] = (3,3),
):
    _ensure_dir(output_dir)
    for file in input_files:
        print(file)
        fig, ax = plt.subplots(figsize=figsize, layout="constrained")
        audio = common.read_audio(file, start=30, duration=30)
        spect = common.make_spectrogram(audio)
        spf = tzanetakis.stereo_panning_features(spect, audio.sampling_rate, 40)
        display.display_spf(spf, "", ax, ylim={"bottom": -0.1, "top": 5})
        fig.savefig(output_dir / f"{file.stem}.pdf")
        plt.close()

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
def hello():
    return _git_root()

if __name__ == "__main__":
    app()
