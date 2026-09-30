import hashlib
import json
from pathlib import Path
from typing import Any, Optional, List, Tuple
from pprint import pprint

from typer import Typer
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm

from algorithms.fip import frequency_intensity_profile
from algorithms.common import read_audio

from datagen import tasks as dgt
from datagen.celery import app as celery_app

app = Typer()
datagen_app = Typer()
multi_app = Typer()
app.add_typer(datagen_app, name="dg")
app.add_typer(multi_app, name="multi")


def _hash(*args: Any) -> str:
    hasher = hashlib.md5()
    for arg in args:
        hasher.update(arg)
    return hasher.hexdigest()


def _hash_series(x: pd.Series) -> str:
    hasher = hashlib.md5()
    for val in x.values:
        if val is None:
            hasher.update('None'.encode())
        elif isinstance(val, float):
            hasher.update(str(val).encode())
        elif isinstance(val, str):
            hasher.update(val.encode())
        else:
            hasher.update(bytes(val))
    return hasher.hexdigest()


# @app.command()
# def dummy():
#     pass


# @app.command()
# def fip(
#     file: Path,
#     output_dir: Path,
#     start: float = 0.0,
#     duration: Optional[float] = None,
#     force: bool = False,
# ):
#     sig = read_audio(file, start=start, duration=duration)
#     freqs, fip = frequency_intensity_profile(sig)
#     hasher = hashlib.sha256()
#     hasher.update(frequency_intensity_profile.__code__.co_qualname.encode())
#     hasher.update(frequency_intensity_profile.__code__.co_code)
#     print(hasher.hexdigest())


@datagen_app.command(name="fip")
def dg_fip(
    file: Path, start: float = 0.0, duration: Optional[float] = None
):
    result = dgt.task_fip.delay(str(file), start, duration).get()
    pprint(result)


@datagen_app.command(name='loudness')
def dg_loudness(
    file: Path, start: float = 0.0, duration: Optional[float] = None
):
    result = dgt.task_loudness.delay(str(file), start, duration).get()
    pprint(result)


class MultiCommand:
    def __init__(self, task, argnames: List[str]):
        self.task = task
        self.argnames = argnames

    def run(self, definition_csv: Path, output_dir: Path):
        task_output_dir = output_dir / self.task.name
        task_output_dir.mkdir(exist_ok=True, parents=True)

        df = pd.read_csv(definition_csv).replace([np.nan], [None])
        df["task"] = None

        try:
            for idx in df.index:
                argvals = df.loc[idx, self.argnames].to_list()
                argdict = dict(zip(self.argnames, argvals))
                task = self.task.delay(**argdict)
                df.loc[idx, "task"] = task

            print("All tasks dispatched")

            for idx in tqdm(df.index):
                try:
                    # if the task threw an exception it will be raised here
                    result = df.loc[idx, "task"].get()
                except Exception as e:
                    print(e)
                    continue
                args = df.loc[idx, self.argnames]
                output = {"args": args.to_dict(), "result": result}
                result_name = _hash_series(args)
                output_file = task_output_dir / str(result_name)
                output_file.write_text(json.dumps(output))

        except KeyboardInterrupt:
            ids = [t.id for t in df['task'] if t is not None]
            celery_app.control.revoke(ids)


@multi_app.command(name="test")
def multi_test(num_tasks: int) -> None:
    # Make sure the output directory exists

    tasks = []
    try:
        for i in range(num_tasks):
            task = dgt.task_wait.delay()
            tasks.append(task)

        print("All tasks dispatched")

        for task in tqdm(tasks):
            result = task.get()

    except KeyboardInterrupt:
        celery_app.control.revoke([t.id for t in tasks])


@multi_app.command(name="spf")
def multi_spf_2(definition_csv: Path, output_dir: Path) -> None:
    MultiCommand(dgt.task_spf, ["filepath", "start", "duration"]).run(
        definition_csv, output_dir
    )


@multi_app.command(name="fip")
def multi_fip_2(definition_csv: Path, output_dir: Path) -> None:
    MultiCommand(dgt.task_fip, ["filepath", "start", "duration"]).run(
        definition_csv, output_dir
    )


@multi_app.command(name="ffprobe")
def multi_ffprobe_2(definition_csv: Path, output_dir: Path) -> None:
    MultiCommand(dgt.task_ffprobe, ["filepath"]).run(definition_csv, output_dir)


@multi_app.command(name="recording-features")
def multi_recording_features(definition_csv: Path, output_dir: Path) -> None:
    MultiCommand(
        dgt.task_recording_features, 
        ["filepath", "start", "duration"]
    ).run(definition_csv, output_dir)


@multi_app.command(name="loudness")
def multi_recording_features(definition_csv: Path, output_dir: Path) -> None:
    MultiCommand(
        dgt.task_loudness, 
        ["filepath", "start", "duration"]
    ).run(definition_csv, output_dir)


if __name__ == "__main__":
    app()
