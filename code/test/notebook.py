import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import matplotlib.pyplot as plt
    import marimo as mo
    import slow
    from versioning import get_module_version
    return get_module_version, mo, slow


@app.cell
def _(get_module_version, slow):
    print(get_module_version("sub"))
    print(get_module_version("slow"))
    print(get_module_version(slow))
    return


@app.cell
def _(mo):
    file = "/Users/richard/Music/archive/09. Tsubasao Kudasai.wav"
    # file = "/Users/richard/Music/freesound/754124__guitarstringtheory__electricguitar001.wav"

    start = mo.ui.slider(start = 0, stop = 100, step=0.1, value=0., label="Start")
    duration = mo.ui.slider(start = 1, stop=5, step=0.1, value=4., label="Duration")
    mo.vstack([start, duration])
    return duration, file, start


@app.cell
def _(fig1, mo):
    mo.mpl.interactive(fig1)
    return


@app.cell
def _(duration, file, slow, start):
    fs, audio = slow.read_file(file, start=start.value, duration=duration.value)
    fs2, audio2 = slow.read_file(file, 0, 4)
    return audio, audio2, fs


@app.cell
def _(audio, audio2, mo, slow):
    fig1 = slow.display_clip(audio)
    fig2 = slow.display_clip(audio2)
    mo.output.append(fig1)
    mo.output.append(fig2)
    return (fig1,)


@app.cell
def _(audio, audio2, fs, mo):
    for a in [audio, audio2]:
        mo.output.append(mo.audio(a,rate=fs))
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
