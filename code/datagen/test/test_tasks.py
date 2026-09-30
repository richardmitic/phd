import pytest
import pyfar as pf
from pathlib import Path

from datagen.tasks import task_spf, task_fip, task_recording_features, task_ffprobe, task_loudness

@pytest.fixture(scope="session")
def mono_file(tmpdir_factory: Path) -> Path:
    sig = pf.signals.noise(44100 * 30)
    fn = tmpdir_factory.mktemp("data").join("mono.flac")
    pf.io.write_audio(sig, str(fn))
    return fn

@pytest.fixture(scope="session")
def stereo_file(tmpdir_factory: Path) -> Path:
    sig = pf.signals.noise(44100 * 30 , rms=[0.707, 0.707])
    fn = tmpdir_factory.mktemp("data").join("stereo.flac")
    pf.io.write_audio(sig, str(fn))
    return fn

@pytest.fixture(scope="session")
def broken_file(tmpdir_factory: Path) -> Path:
    fn = tmpdir_factory.mktemp("data").join("broken.mp3")
    fn.write(b'nothingtoseehere')
    return fn

def test_tasks(mono_file: Path, stereo_file: Path, broken_file: Path):

    rec_feat = {
        "clipping",
        "stereo_width",
        "average_phase_difference",
        "mono_compatibility",
        "compression",
    }

    fip_feat = {
        "freqs",
        "fip"
    }

    ff_feat = {
        "channel_count",
        "sample_rate",
        "codec",
        "duration",
        "bitrate",
    }

    loud_feat = {
        "integrated_loudness",
        "loudness_range",
    }

    assert "spf" in task_spf(mono_file)
    assert rec_feat == set(task_recording_features(mono_file).keys())
    assert fip_feat == set(task_fip(mono_file).keys())
    assert ff_feat == set(task_ffprobe(mono_file).keys())
    assert loud_feat == set(task_loudness(mono_file).keys())
    
    assert "spf" in task_spf(stereo_file)
    assert rec_feat == set(task_recording_features(stereo_file).keys())
    assert fip_feat == set(task_fip(stereo_file).keys())
    assert ff_feat == set(task_ffprobe(stereo_file).keys())
    assert loud_feat == set(task_loudness(stereo_file).keys())

    assert "error" in task_spf(broken_file)
    assert "error" in task_recording_features(broken_file)
    assert "error" in task_fip(broken_file)
    assert "error" in task_ffprobe(broken_file)
    assert "error" in task_loudness(broken_file)