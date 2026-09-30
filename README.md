# Sound React Project

An audio-reactive particle visual for TouchDesigner, built entirely from Python scripts.

Instead of a `.toe` file, this repo holds three scripts that construct the whole network —
audio analysis, a GPU particle simulation, and the render/post chain — inside a blank project.
A fourth workflow reads your hand-tuning back out and writes it into the scripts, so the
visual and its tuning live in source control as readable Python.

## Requirements

TouchDesigner (developed against build 2025.33230) — nothing else.

The project uses three stock Palette components (`audioAnalysis`, `bloom`, `feedback`).
The scripts locate them inside your own TouchDesigner install, so there is nothing to
download and no paths to configure.

## Setup

1. Open a new TouchDesigner project.
2. Create a **Base COMP** named `project1` (the scripts build into `/project1`).
3. Inside it, create three **Text DATs** named `audio_setup`, `pop_setup` and
   `save_settings`. Point each one's **File** parameter at the matching `.py` file
   and pulse **Load on Start**.
4. Open the Textport (`Alt+T`) and run, in order:

```python
op('/project1/audio_setup').run()
op('/project1/pop_setup').run()
```

Set the song by editing `AUDIO_FILE` at the top of `audio_setup.py`, or by changing the
**File** parameter on `audiofilein1` once it exists.

The output appears in a separate window driven by `window1`.

## The scripts

**`audio_setup.py`** — plays an audio file and analyses it. Builds `audiofilein1`,
the `audioAnalysis` component, `null1` (its nine channels: low, mid, high, kick, snare,
rhythm, smsd, fmsd, spectralCentroid), `speed1` (which integrates those channels into
continuously advancing values), `null2` (the raw stereo waveform) and `audiodevout1`.

Per-song tuning lives in the `ANALYSIS_SETTINGS` dictionary at the top.

**`pop_setup.py`** — builds the visual. The raw waveform becomes a line of points, which
seed a particle system running in a GPU feedback loop; two noise fields and a twist deform
the cloud, points straying too far are culled, and the result is rendered and post-processed.

The three audio-to-visual mappings are constants at the top of the file:

```python
MAP_LOW   = "op('speed1')['mid']*0.5"    # noise2 Translate 4D — broad displacement
MAP_FMSD  = "op('speed1')['fmsd']"       # noise1 Translate 4D — fine displacement
MAP_SNARE = "op('null1')['snare']*0.5"   # math1 Multiply — blend weight between the two
```

Any of the nine analysis channels can be substituted. Use `null1` for a raw 0–1 value that
tracks the music moment to moment, or `speed1` for its integral, which always advances
forward and so never repeats.

**`save_settings.py`** — the round trip. Tune the song, the `audioAnalysis` controls, or the
three mapping expressions by hand in TouchDesigner, then run:

```python
op('/project1/save_settings').run()
```

It reads the live values and rewrites `AUDIO_FILE`, `ANALYSIS_SETTINGS` and the three
`MAP_*` constants in place, so the next rebuild reproduces exactly what you tuned.

## Signal flow

```
audiofilein1 ──┬── audiodevout1                  (monitoring)
               ├── null2 ─────────────────┐      (raw stereo waveform)
               └── audioAnalysis ── null1 ─┼── speed1
                                           │
  chopto1 ◄────────────────────────────────┘     (waveform → points)
     └── particle1 ── random1 ── null3 ──┬── feedback1 ──┐
                                         └── merge1 ◄────┘
             merge1 ── mathmix1 ── mathmix2 ── noise2 ──┬── noise1 ──┐
                                                        └── math1 ───┴── mathmix3
             mathmix3 ── twist1 ── delete1 ── endfeedback ──► back to feedback1
                                        └── geo1 ── render1
             render1 ── feedback ── bloom ── rgbkey1 ── null4 ── window1
```

`feedback1` and `endfeedback` form the particle simulation loop; the `feedback` TOP is a
separate image-level trail. Press **1** to restart the simulation.

## Notes

- `pointsprite1`'s colour and size are fixed, so the audio reactivity is expressed entirely
  through motion and shape. Driving colour or size from audio is unexplored.
- Using an integrated channel (`speed1`) for a blend weight makes it grow without bound.
  `MAP_SNARE` deliberately uses the raw `null1` value so the weight stays within 0–1.
- Live audio input works by replacing `audiofilein1` with an Audio Device In CHOP; the rest
  of the chain is unchanged. A loopback device such as VB-Cable captures system audio.
