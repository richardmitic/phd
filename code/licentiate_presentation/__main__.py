from enum import Enum
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
from scipy.spatial import ConvexHull


from cache_to_disk import cache_to_disk
from typing import List, Tuple, Any, Optional, Dict, Annotated

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

    for file, ax, in zip(input_files, axes.flat):
        print(file)
        asf = __get_asf(file)
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


@cache_to_disk()
def __get_ph(file: Path) -> Dict[str, Any]:
    audio = common.read_audio(file, start=30, duration=30)
    spect = common.make_spectrogram(audio)
    ph_gomez = gomez.panning_histogram(spect, 65)
    ph_sarroff = sarroff.panning_histogram(np.abs(spect), 32)
    ph_sarroff /= np.sum(ph_sarroff)
    return {
        "gomez": ph_gomez,
        "sarroff": ph_sarroff,
    }

@cache_to_disk()
def __get_spf(file: Path) -> tzanetakis.StereoPanningFeatures:
    audio = common.read_audio(file, start=30, duration=30)
    spect = common.make_spectrogram(audio)
    return tzanetakis.stereo_panning_features(spect, audio.sampling_rate, 40)


# calculating ASF is really slow so cache the results
@cache_to_disk()
def __get_asf(file: Path):
    audio = common.read_audio(file, start=30, duration=30)
    coch = tardieu.cochleagram(audio, 0.2, 0.1, 70)
    return tardieu.amplitude_stereo_features(coch) 


class SipType(Enum):
    gomez = "gomez"
    sarroff = "sarroff"
    spf = "spf"
    asf = "asf"


def expand_from_centroid(points, distance=0.618):
    centroid = np.mean(points, axis=0)
    direction_vectors = points - centroid
    magnitudes = np.linalg.norm(direction_vectors, axis=1, keepdims=True)
    # Avoid division by zero if a point sits exactly on the centroid
    magnitudes[magnitudes == 0] = 1.0
    unit_vectors = direction_vectors / magnitudes
    expanded_points = points + (unit_vectors * distance)
    return expanded_points


@app.command()
def cluster(
    files: List[Path],
    sip: SipType,
    output: Optional[Path] = None,
    seed: Optional[int] = None,
):
    from sklearn.manifold import TSNE
    from sklearn.cluster import KMeans
    from matplotlib import rcParams
    from matplotlib.patches import Ellipse
    # rcParams["text.usetex"] = True

    print(sip)
    
    X = []
    for file in files:
        if sip == SipType.gomez:
            X.append(__get_ph(file)["gomez"])
        elif sip == SipType.sarroff:
            X.append(__get_ph(file)["sarroff"])
        elif sip == SipType.spf:
            X.append(__get_spf(file))
        else:
            assert False
    X = np.stack(X)
    print(X)

    tsne = TSNE()
    Y = tsne.fit_transform(X)
    print(Y.shape)

    colors = plt.color_sequences['tab10']
    n_clusters = 6

    kmeans = KMeans(n_clusters=n_clusters, random_state=seed)
    K = kmeans.fit_predict(X)

    central_tracks = []
    for centroid in kmeans.cluster_centers_:
        dist = np.linalg.norm(X - centroid, axis=1)
        closest_idx = np.argsort(dist)[0]
        central_tracks.append(closest_idx)

    print(np.asarray(files, dtype=str)[central_tracks])

    fig, ax = plt.subplot_mosaic(
        "XXAB\nXXCD\nXXEF",
        figsize=(8,4), 
        layout='constrained'
    )

    letters = "ABCDEFGHI"

    for point, cluster in zip(Y, K):
        letter = letters[cluster]
        color = colors[cluster]
        ax['X'].text(
            x=point[0], 
            y=point[1], 
            horizontalalignment='center',
            verticalalignment='center',
            s=letter, 
            color=color, 
            fontweight='bold'
        )

    for i in range(n_clusters):
        letter = letters[i]
        if sip in [SipType.gomez, SipType.sarroff]:
            display.draw_panning_histogram(
                X[central_tracks[i]], 
                ax[letter], 
                None, # type: ignore
                None, # type: ignore
                y_label=None,
                plot_kwargs={"label": letter, "color": colors[i]},
                x_label=None,
            )
        elif sip == SipType.spf:
            display.display_spf(X[central_tracks[i]], letter, ax[letter])
    
    for letter in "ABCD":
        ax[letter].set_xticks([])
    for letter in "EF":
        ax[letter].set_xlabel("Azimuth")

    for i in range(n_clusters):
        points = expand_from_centroid(Y[K == i])
        if len(points) >= 3:
            hull = ConvexHull(points)
            verts = np.append(hull.vertices, hull.vertices[0])
            ax['X'].plot(points[verts,0], points[verts,1], color=colors[i])
        else:
            # Define the two points
            p1 = points[0]
            p2 = points[1] if len(points) == 2 else points[0]

            # Calculate center midpoint
            center = (p1 + p2) / 2

            # Calculate distance (width of ellipse) and add padding
            delta = p2 - p1
            width = np.linalg.norm(delta) + 0.4  # +something for padding/margin
            height = width * 0.8 # Adjust height/aspect ratio as needed

            # Calculate angle in degrees
            angle = np.degrees(np.arctan2(delta[1], delta[0]))

            # Create the ellipse patch
            ellipse = Ellipse(
                xy=center,
                width=width,
                height=height,
                angle=angle,
                edgecolor=colors[i],
                facecolor="none",
            )
            ax['X'].add_patch(ellipse)

    padding = 1
    mins = np.min(Y, axis=0)
    maxs = np.max(Y, axis=0)
    ax['X'].set_xbound(mins[0] - padding, maxs[0] + padding)
    ax['X'].set_ybound(mins[1] - padding, maxs[1] + padding)
    ax['X'].set_xlabel("TSNE dimension 0")
    ax['X'].set_ylabel("TSNE dimension 1")

    if output:
        fig.savefig(output)
    else:
        plt.show()



@app.command()
def delete_cache(func: str):
    from cache_to_disk import delete_disk_caches_for_function
    delete_disk_caches_for_function(func)

if __name__ == "__main__":
    app()
