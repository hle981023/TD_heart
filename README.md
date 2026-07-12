# Guardian Heart — TouchDesigner edition

A native TouchDesigner build of the Guardian Heart experience: the webcam feeds
MediaPipe hand tracking, the **same unit-tested gesture logic as the web app**
turns landmarks into stable states, and TouchDesigner renders the artifacts and
heart effects.

This project is **independent of the web version** — it reuses only the
MediaPipe model and the gesture/effect logic (ported to Python), so both stay in
sync behaviourally while you build the visuals in TD.

## Requirements

- TouchDesigner 2022.24000+ (Python 3.11 builds recommended)
- A webcam
- MediaPipe installed into TouchDesigner's Python

### Install MediaPipe into TD's Python

Use the Python that ships inside TouchDesigner (not system Python), matching TD's
version. On macOS:

```bash
# Path shown for a typical install — adjust to your TD version.
"/Applications/TouchDesigner.app/Contents/Frameworks/Python/bin/python3" \
  -m pip install --upgrade mediapipe numpy
```

On Windows the interpreter is under `C:\Program Files\Derivative\TouchDesigner\bin\`.
If TD can't find the packages, add the site-packages folder in
`Preferences → General → Python 64-bit Module Path`.

## Build the network

1. Open a new project and **save it into this folder** (so `project.folder`
   resolves to the repo root, where `models/` and `guardian/` live).
2. Open a Textport (`Alt/Opt+T`) and run:

   ```python
   exec(open(project.folder + '/td/build_network.py').read())
   ```

This creates `/guardian_heart` with the full data pipeline and a starter visual
scaffold. Re-running rebuilds it from scratch.

## Node map

```
guardian_heart/
  videoin        Video Device In TOP      webcam (1280x720)
  hands          Script CHOP              MediaPipe landmarks  (callbacks: hand_source)
  gesture        Script CHOP              classify + machine + schedule (callbacks: gesture_engine)
  gesture_out    Null CHOP                clean reference for the whole app
  preview        Flip TOP                 mirrored camera preview
  egg / lock     Geometry COMP            two artifacts, positioned from gesture_out
  cam / key_light / render / composite / out
```

### `gesture_out` channels

| Channel | Meaning |
| --- | --- |
| `kind_index` | stable gesture (see `guardian/types.py` `GESTURE_KINDS` order) |
| `confidence`, `changed` | detection confidence; 1 on the frame the stable state changes |
| `origin_x`, `origin_y` | effect origin, normalized (0..1) |
| `left_valid` / `left_x` / `left_y` | left (egg) hand index point |
| `right_valid` / `right_x` / `right_y` | right (lock) hand index point |
| `fire_small`, `fire_strong` | `1` on the frame a heart should spawn |
| `beam`, `shockwave` | entry-only burst flags |

`kind_index` encoding: `0 idle, 1 egg-ready, 2 lock-ready, 3 both-ready,
4 fusing, 5 armed, 6 finger-heart, 7 big-heart, 8 releasing`.

## Gestures

| Gesture | Result |
| --- | --- |
| One index finger, screen-left | Summon the egg (`egg-ready`) |
| One index finger, screen-right | Summon the lock (`lock-ready`) |
| Both index fingers | `both-ready` |
| Finger heart (small two-hand heart) | `fire_small` pulses (~4/sec) + `beam` |
| Big heart (large two-hand heart) | `fire_strong` every ~900ms + `shockwave` |

A pose must hold 150ms before it commits; releasing fades through `releasing`
for 300ms — identical to the web app.

## Tuning the visuals

The build script lays down the reactive data and placeholder geometry. Do the
art in the GUI:

- **Artifacts:** replace the placeholder Sphere/Torus SOPs with `File In SOP`
  loading `../visual art/.worktrees/guardian-heart/public/models/*.glb`, or model
  natively. Positions/scale/spin are already bound to `gesture_out`.
- **Heart projectiles:** add a `Particle GPU` (or instanced Geometry) whose birth
  is gated by `gesture_out['fire_small']` / `['fire_strong']`, emitted at
  (`origin_x`, `origin_y`). Strong hearts: larger scale + higher velocity.
- **Beam / shockwave:** trigger a `Trigger CHOP` from `beam` / `shockwave` to
  drive a vertical-glow TOP and an expanding-ring SOP.
- **Bloom:** a `Bloom TOP` on the `render` output sells the additive look.

## Verify the ported logic

The gesture/effect core is a faithful port of the web app's tested modules and
carries the same tests:

```bash
python3 tests/test_guardian.py    # or: pytest
```

All six cases mirror the web app's `classify`, `machine`, and `effectSchedule`
tests.

## Alternative: dotsimulate MediaPipe plugin

If you prefer not to pip-install MediaPipe, the community
**MediaPipe TouchDesigner** component outputs hand landmarks as CHOP channels
directly. Feed those into `gesture` instead of the `hands` Script CHOP — remap
its channels to the `h{i}_lm{k}_{x,y,z}` layout `gesture_engine._read_hands`
expects (or adjust that reader).
