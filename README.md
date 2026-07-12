# Guardian Heart — TouchDesigner edition

A native TouchDesigner build of the Guardian Heart experience. A small external
Python process does the webcam + MediaPipe hand tracking and the **same
unit-tested gesture logic as the web app**, then streams the gesture state into
TouchDesigner over OSC. TD renders the artifacts and heart effects.

## Why an external process (macOS)

TouchDesigner's bundled Python is a hardened runtime that refuses to load
pip-installed native extensions — importing MediaPipe fails with *"different Team
IDs"*. So MediaPipe runs in a normal `venv` (`runner/hand_runner.py`) and only
the resulting numbers cross into TD via OSC. TD needs **no Python packages** for
this path — just the built-in **OSC In CHOP**.

```
webcam ─▶ hand_runner.py (MediaPipe + gesture logic) ─OSC▶ TD OSC In CHOP ─▶ visuals
```

## Requirements

- TouchDesigner 2022.24000+
- Python 3.9+ with a webcam (for the runner venv)
- macOS or Windows

## 1. Set up the runner (one time)

From this project folder:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r runner/requirements.txt
```

Verify without a camera (sends one synthetic "big heart" frame over OSC):

```bash
.venv/bin/python runner/hand_runner.py --selftest
```

## 2. Build the TD network (one time)

1. Open TouchDesigner, **Save As** into this project folder (so `project.folder`
   resolves here).
2. Textport (`Alt/Opt+T`), run:

   ```python
   exec(open(project.folder + '/td/build_network.py').read())
   ```

This creates `/guardian_heart` (an `OSC In CHOP` on port **7000** → `gesture_out`
null → two artifacts). Re-running rebuilds it.

## 3. Run

```bash
.venv/bin/python runner/hand_runner.py --preview
```

- Grant camera permission when macOS asks.
- `--preview` opens a local window with landmark dots + the current state.
- Move a hand: `guardian_heart/gesture_out` channels update live in TD.

Stop with `Esc` (preview) or `Ctrl+C`.

## `gesture_out` channels

| Channel | Meaning |
| --- | --- |
| `kind_index` | stable gesture (encoding below) |
| `confidence`, `changed` | detection confidence; 1 on the frame the state changes |
| `origin_x`, `origin_y` | effect origin, normalized 0..1 |
| `left_valid` / `left_x` / `left_y` | left (egg) hand index point |
| `right_valid` / `right_x` / `right_y` | right (lock) hand index point |
| `fire_small`, `fire_strong` | `1` on the frame a heart should spawn |
| `beam`, `shockwave` | entry-only burst flags |

`kind_index`: `0 idle, 1 egg-ready, 2 lock-ready, 3 both-ready, 4 fusing,
5 armed, 6 finger-heart, 7 big-heart, 8 releasing`.

## Gestures

| Gesture | Result |
| --- | --- |
| One index finger, screen-left | Summon the egg (`egg-ready`) |
| One index finger, screen-right | Summon the lock (`lock-ready`) |
| Both index fingers | `both-ready` |
| Finger heart (small two-hand heart) | `fire_small` (~4/sec) + `beam` |
| Big heart (large two-hand heart) | `fire_strong` (~every 900ms) + `shockwave` |

A pose must hold 150ms before it commits; releasing fades through `releasing`
for 300ms — identical to the web app.

## Tuning the visuals

The build script lays down reactive data and placeholder geometry. Do the art in
the GUI:

- **Artifacts:** replace the placeholder Sphere/Torus SOPs with `File In SOP`
  loading `../visual art/.worktrees/guardian-heart/public/models/*.glb`.
  Positions/scale/spin are already bound to `gesture_out`.
- **Heart projectiles:** a `Particle GPU` (or instanced Geometry) whose birth is
  gated by `gesture_out['fire_small']` / `['fire_strong']`, emitted at
  (`origin_x`, `origin_y`). Strong hearts: larger scale + higher velocity.
- **Beam / shockwave:** a `Trigger CHOP` from `beam` / `shockwave` drives a
  vertical-glow TOP and an expanding-ring SOP.
- **Bloom:** a `Bloom TOP` on `render` sells the additive look.

## Verify the ported logic

The gesture/effect core is a faithful port of the web app's tested modules:

```bash
python3 tests/test_guardian.py    # or: pytest
```

All six cases mirror the web app's `classify`, `machine`, and `effectSchedule`
tests.

## Project layout

```
guardian/     gesture core, unit-tested, shared by the runner (and TD path)
runner/       hand_runner.py external MediaPipe -> OSC sensor + requirements
td/           build_network.py (OSC) + in-TD Script CHOP callbacks (advanced)
models/       hand_landmarker.task (same model as the web app)
tests/        test_guardian.py
```

## Advanced: run MediaPipe inside TD

On platforms where TD's Python *can* load MediaPipe (e.g. Windows, or a re-signed
macOS install), `td/hand_source.py` and `td/gesture_engine.py` are Script CHOP
callbacks that do the tracking in-process — no OSC. See their headers. On stock
macOS use the OSC runner above.
