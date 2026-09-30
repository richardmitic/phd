import subprocess
import json
import time
from pathlib import Path
from typing import Optional, Any, Callable

import numpy as np
import pyloudnorm

from datagen.celery import app
from algorithms import mourgela
from algorithms.common import chunked
from algorithms.tzanetakis import stereo_panning_features
from algorithms.fip import frequency_intensity_profile
from algorithms.common import read_audio, upmix_to_stereo

def _map(val: Optional[Any], func: Callable) -> Optional[Any]:
    return func(val) if val is not None else None

# 2. FFprobe Task
@app.task(bind=True)
def task_ffprobe(self, filepath: str):
    """
    Runs ffprobe on a given file to extract metadata.
    """
    try:
        # Command to get metadata in JSON format
        command = [
            'ffprobe',
            '-v', 'error',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            filepath
        ]
        
        # Run subprocess and capture output
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # The output is a JSON string containing stream and format details
        metadata = json.loads(result.stdout)

        # Simple extraction of required fields (Bitrate usually needs deeper parsing)
        format_info = metadata.get('format', {})
        streams = metadata.get('streams', [])
        
        # For simplicity, we grab the container stream info if available
        channel_count = streams[0].get('channels', None)
        sample_rate = _map(streams[0].get('sample_rate', None), int)
        codec = streams[0].get('codec_name', None)
        duration = _map(streams[0].get('duration', None), float)
        
        # Bitrate handling is complex; we'll return the overall format bitrate if available
        bitrate = _map(format_info.get('bit_rate'), int)
        
        return {
            "channel_count": channel_count,
            "sample_rate": sample_rate,
            "codec": codec,
            "duration": duration,
            "bitrate": bitrate
        }

    except subprocess.CalledProcessError as e:
        return {"error": f"FFprobe failed: {e.stderr}"}
    except Exception as e:
        return {"error": f"{type(e).__name__} {e}"}


# 3. SPF Task
@app.task(bind=True)
def task_spf(
    self,
    filepath: str, 
    start: float = 0.,
    duration: Optional[float] = None,
    fft_size: int = 1024,
    hop_size: int = 512,
    M: int = 40,
):
    """
    Placeholder task for custom processing logic (e.g., signal processing).
    """
    try:
        audio = read_audio(filepath, start, duration)
        if audio.cshape == (1,):
            return {
                "spf": np.zeros(16).tolist()
            }
        spect = np.fft.rfft(chunked(audio, fft_size, hop_size))
        spf = stereo_panning_features(spect, audio.sampling_rate, M)

        return {
            "spf": list(spf),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__} {e}"}


# 2. FIP Task
@app.task(bind=True)
def task_fip(
    self, 
    filepath: str, 
    start: float = 0., 
    duration: Optional[float] = None
):
    """
    Calulates frequency intensity profile.
    """
    try:
        audio = read_audio(filepath, start=start, duration=duration)
        freqs, fip = frequency_intensity_profile(audio)
        
        return {
            "freqs": list(freqs),
            "fip": list(fip),
        }
    
    except Exception as e:
        return {"error": f"{type(e).__name__} {e}"}


@app.task(bind=True)
def task_recording_features(
    self,
    filepath: str, 
    start: float = 0., 
    duration: Optional[float] = None
):
    """Features from Mourgela 2002"""
    try:
        audio = read_audio(filepath, start, duration)
        return {
            "clipping": mourgela.clipping(audio),
            "stereo_width": mourgela.stereo_width(audio),
            "average_phase_difference": mourgela.averge_phase_difference(audio),
            "mono_compatibility": mourgela.mono_compatibility(audio),
            "compression": mourgela.compression(audio),
        }    
    except Exception as e:
        return {"error": f"{type(e).__name__} {e}"}


@app.task(bind=True)
def task_loudness(
    self,
    filepath: str,
    start: float = 0., 
    duration: Optional[float] = None
):
    """ITU-R BS.1770-4."""
    try:
        audio = read_audio(filepath, start, duration)
        meter = pyloudnorm.Meter(audio.sampling_rate)
        audio_data = audio.time.T
        return {
            "integrated_loudness": meter.integrated_loudness(audio_data),
            "loudness_range": meter.loudness_range(audio_data),
        }    
    except Exception as e:
        return {"error": f"{type(e).__name__} {e}"}



@app.task(bind=True)
def task_wait(
    self, 
    duration: float = 1., 
):
    time.sleep(duration)