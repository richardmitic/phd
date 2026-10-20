import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
import librosa
from matplotlib.path import Path
from typing import Optional, Dict, Tuple, Any, List

from algorithms.tzanetakis import StereoPanningFeatures
from algorithms.common import PanningHistogram, TFRegion

def display_spf(
    spf: StereoPanningFeatures, 
    title: str, 
    ax: plt.Axes, 
    ylim: Optional[Dict[str, float]] = None,
    xlim: Optional[Dict[str, float]] = None,
):
    mm = spf[0:4]
    sm = spf[4:8]
    ms = spf[8:12]
    ss = spf[12:16]
    xl = np.arange(4) + (0.618 / 2)
    xr = np.arange(4) + (0.618)
    # squiggly_marker = Path([(-1, 0), (-0.5,0.5), (0.5,-0.5), (1, 0)], closed=False)
    n_points = 20
    marker_y = np.sin(np.linspace(0,2*np.pi,n_points)) * 0.5
    marker_x = np.linspace(-1,1,n_points)
    squiggly_marker = Path(list(zip(marker_x, marker_y)), closed=False)
    ax.errorbar(xl, mm, yerr=ms, label='Slow panning', color='k', marker="_", linestyle='none', linewidth=0.618)
    ax.errorbar(xr, sm, yerr=ss, label='Fast panning', color='k', marker=squiggly_marker, markerfacecolor='none', linestyle='none', linewidth=0.618)
    ax.set_ylim(bottom=-0.1)
    ax.set_title(title)
    ax.set_ylim(**ylim)
    ax.set_xlim(**xlim)
    ax.set_xticks([0.5,1.5,2.5,3.5], ["Full", "Low", "Mid", "High"])
    ax.set_xlabel("Frequency band")


def _quartiles(arr: NDArray[np.floating]) -> NDArray[np.floating]:
    return np.interp([0.25, 0.75], np.cumsum(arr), np.linspace(0, len(arr), len(arr)))

def draw_panning_histogram(
    hist: PanningHistogram,
    ax: plt.Axes,
    title: str,
    ylim: Tuple[float, float],
    grid: bool = False,
    quartiles: bool = False,
    **plot_kwargs: Dict[Any, Any], 
):
    ax.plot(hist, **plot_kwargs)
    ax.set_yticks([])
    ax.set_title(title)
    ax.set_ylim(ylim)
    l = 0
    r = hist.shape[0] - 1
    c = int(hist.shape[0] / 2)
    ax.set_xticks([l,c,r], labels=['L', 'C', 'R'])
    ax.set_xticks(np.linspace(0, len(hist) - 1, 7), minor=True)
    if grid:
        ax.grid(axis='x', which='major', linewidth=0.618, linestyle='dashed')
        ax.grid(axis='x', which='minor', linewidth=0.618/2, linestyle='dotted')
    if quartiles:
        col = plot_kwargs.get('color', 'red')
        ax.vlines(_quartiles(hist), *ylim, color=col, linestyles='solid', linewidth=0.618)
    ax.set_xlabel("Azimuth")
    ax.set_ylabel("Normalized histogram value")
    ax.legend(loc='upper left')


def draw_spectograms(
    spects: List[TFRegion],
):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(spects), 2, sharex=True)
    axes = np.atleast_2d(axes)
    for ax_row, ss in zip(axes, spects):
        ax_row[0].imshow(librosa.amplitude_to_db(np.rot90(np.abs(ss[0])), ref=np.max), aspect='auto', cmap='magma')
        ax_row[1].imshow(librosa.amplitude_to_db(np.rot90(np.abs(ss[1])), ref=np.max), aspect='auto', cmap='magma')
    return fig
