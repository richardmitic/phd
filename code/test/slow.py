import time
import numpy as np
import multiprocessing as mp
import matplotlib.pyplot as plt
from scipy.io import wavfile

VERSION="2.2.2"

def provide_slow(delay, x):
    delay = delay + (np.random.random() * 4)
    x = x + np.random.randint(10)
    time.sleep(delay)
    print(f"delayed by {delay} and {x}")
    X = np.linspace(0, x, 48000)
    return np.cos(X) + 1j * np.sin(X) 

def provide_slow_single_arg(arg):
    return provide_slow(*arg)

def para(func, args):
    with mp.Pool() as pool:
        return pool.map(func, args, chunksize=1)

def save_image(waves):
    fig, axis = plt.subplots(1, 1)
    for w in waves:
        axis.plot(w.imag)
    fig.savefig("out.pdf")
    return fig

def read_file(file, start=0., duration=30.):
    fs, samples = wavfile.read(file)
    samples = samples.T
    start_sample = int(start * fs)
    duration_samples = int(duration * fs)
    clip = samples[:, start_sample:start_sample+duration_samples] 
    return fs, clip

def display_clip(clip):
    fig, axis = plt.subplots(1, 1)
    for channel in clip:
        axis.plot(channel)
    return fig