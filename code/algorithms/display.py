from nbformat.sign import algorithms
import tarfile
from sympy.functions.combinatorial.numbers import nD
import math
import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
import librosa
from matplotlib.path import Path
from typing import Optional, Dict, Tuple, Any, List
import pyfar as pf
from python_auditory_toolbox import auditory_toolbox as pat

from algorithms.tzanetakis import StereoPanningFeatures
from algorithms.tardieu import AmplitudeStereoFeatures
from algorithms.common import PanningHistogram, TFRegion, polar_to_cartesian

def rotate_matrix(
    x: NDArray[np.floating], 
    y: NDArray[np.floating], 
    angle: float,
    x_shift: float = 0.,
    y_shift: float = 0., 
    units="DEGREES"
):
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

def display_spf(
    spf: StereoPanningFeatures, 
    title: str, 
    ax: plt.Axes, 
    ylim: Optional[Dict[str, float]] = None,
    xlim: Optional[Dict[str, float]] = None,
    xlabel: Optional[str] = "Frequency band",
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
    ax.set_title(title)
    if ylim is not None:
        ax.set_ylim(**ylim)  # type: ignore
    if xlim is not None:
        ax.set_xlim(**xlim)  # type: ignore
    ax.set_xticks([0.5,1.5,2.5,3.5], ["Full", "Low", "Mid", "High"])
    ax.set_xlabel(xlabel)  # type: ignore


def _quartiles(arr: NDArray[np.floating]) -> NDArray[np.floating]:
    return np.interp([0.25, 0.75], np.cumsum(arr), np.linspace(0, len(arr), len(arr)))

def draw_panning_histogram(
    hist: PanningHistogram,
    ax: plt.Axes,
    title: str,
    ylim: Tuple[float, float],
    grid: bool = False,
    quartiles: bool = False,
    plot_kwargs: Dict[Any, Any] = {},
    x_label: Optional[str] = "Azimuth",
    y_label: Optional[str] = "Normalized histogram value",
    legend: bool = True,
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
    ax.set_xlabel(x_label) # type: ignore
    ax.set_ylabel(y_label) # type: ignore
    if legend:
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


def draw_goniometer(
    audio: pf.Signal,
    ax: plt.Axes,
):
    from numpy import pi
    from matplotlib.collections import LineCollection

    def _colored_line(
        x: NDArray[np.floating], 
        y: NDArray[np.floating], 
        c, 
        ax=None, 
        **lc_kwargs
    ):
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

        lc_kwargs["alpha"] = c
        lc = LineCollection(segments, **lc_kwargs)  # type: ignore

        # Plot the line collection to the axes
        ax = ax or plt.gca()
        ax.add_collection(lc)

        return lc

    # main figure
    x, y = rotate_matrix(audio.time[0], audio.time[1], 45)

    # draw circles
    for r in [0.25, 0.5, 0.75, 1]:
        M = 100
        xc = np.cos(np.linspace(0, 2 * np.pi, M)) * r
        yc = np.sin(np.linspace(0, 2 * np.pi, M)) * r
        ax.plot(xc, yc, color="grey", alpha=1, linewidth=0.5, linestyle="dotted", solid_capstyle='round')

    # Draw left, centre, and right markers
    line_lx, line_ly = polar_to_cartesian(1, [-pi / 4, 3 * pi / 4])
    line_cx, line_cy = polar_to_cartesian(1, [-pi / 2, -3 * pi / 2])
    line_rx, line_ry = polar_to_cartesian(1, [pi / 4, -3 * pi / 4])
    ax.plot(
        line_lx, line_ly, color="grey", alpha=1, linewidth=0.5, linestyle="dotted", solid_capstyle='round'
    )
    ax.plot(
        line_cx, line_cy, color="grey", alpha=1, linewidth=0.5, linestyle="dotted", solid_capstyle='round'
    )
    ax.plot(
        line_rx, line_ry, color="grey", alpha=1, linewidth=0.5, linestyle="dotted", solid_capstyle='round'
    )

    text_rx, text_ry = polar_to_cartesian(1.1, pi / 4)
    text_cx, text_cy = polar_to_cartesian(0.9, pi / 2 + 0.1)
    text_lx, text_ly = polar_to_cartesian(1.1, 3 * pi / 4)
    ax.text(
        text_rx,
        text_ry,
        "R",
        horizontalalignment="center",
        verticalalignment="center",
        transform=ax.transData,
        color="dimgrey",
    )
    ax.text(
        text_cx,
        text_cy,
        "C",
        horizontalalignment="center",
        verticalalignment="center",
        transform=ax.transData,
        color="dimgrey",
    )
    ax.text(
        text_lx,
        text_ly,
        "L",
        horizontalalignment="center",
        verticalalignment="center",
        transform=ax.transData,
        color="dimgrey",
    )
    
    # draw audio trace
    c = np.linspace(0, 0.618, audio.n_samples)
    _colored_line(
        x, y, c, 
        ax=ax, 
        color="k", 
        linewidth=1,
    )

    # set limits
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)

    # Don't display ticks
    ax.set_xticks([])
    ax.set_yticks([])


def display_asf(asf: AmplitudeStereoFeatures, ax: plt.Axes, freqs: NDArray[np.floating], symxlim: float, title: str = "", xlabel: str | None = None):
    # These frequencies are implicit in the calculation of ASF. Not great, but it'll do.
    # freqs = pat.ErbSpace(low_freq=30, high_freq=44100/2, n=70)[::-1]
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
    ax.set_xlim(left=-symxlim, right=symxlim)
    ax.set_xlabel(xlabel) # type: ignore
    ax.set_title(title)