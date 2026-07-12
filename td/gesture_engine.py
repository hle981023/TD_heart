"""Script CHOP callback: hand landmarks -> stable gesture + effect triggers.

Wire this as the callback DAT of a `Script CHOP` whose first input is the
`hands` Script CHOP (hand_source.py). It reuses the unit-tested `guardian`
package so its behaviour is identical to the web app.

Outputs (one sample):
    kind_index          stable GestureKind, encoded via guardian.KIND_TO_INDEX
    confidence, changed
    origin_x, origin_y  effect origin (normalized), defaults to 0.5, 0.5
    left_valid, left_x, left_y
    right_valid, right_x, right_y
    fire_small, fire_strong   1 on the frame a heart should spawn, else 0
    beam, shockwave           entry-only flags (1/0)
"""

import os
import sys

# Make the sibling `guardian` package importable from inside TouchDesigner.
_PROJECT = project.folder  # noqa: F821
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from guardian.classify import classify_hands  # noqa: E402
from guardian.effect_schedule import (  # noqa: E402
    advance_effect_schedule,
    create_effect_schedule,
)
from guardian.geometry import vec3  # noqa: E402
from guardian.machine import GestureMachine  # noqa: E402
from guardian.types import HandSample, KIND_TO_INDEX  # noqa: E402

MAX_HANDS = 2
_MACHINE_KEY = "guardian_machine"
_SCHEDULE_KEY = "guardian_schedule"


def _state():
    machine = me.fetch(_MACHINE_KEY, None)  # noqa: F821
    if machine is None:
        machine = GestureMachine()
        me.store(_MACHINE_KEY, machine)  # noqa: F821
    schedule = me.fetch(_SCHEDULE_KEY, None)  # noqa: F821
    if schedule is None:
        schedule = create_effect_schedule()
        me.store(_SCHEDULE_KEY, schedule)  # noqa: F821
    return machine, schedule


def _read_hands(source):
    if source is None:
        return []
    n = int(source["n_hands"].eval()) if "n_hands" in source else 0
    hands = []
    for i in range(min(n, MAX_HANDS)):
        if not source[f"h{i}_valid"].eval():
            continue
        landmarks = [
            vec3(
                source[f"h{i}_lm{k}_x"].eval(),
                source[f"h{i}_lm{k}_y"].eval(),
                source[f"h{i}_lm{k}_z"].eval(),
            )
            for k in range(21)
        ]
        handedness = "Left" if source[f"h{i}_hand"].eval() < 0.5 else "Right"
        hands.append(HandSample(handedness, landmarks, source[f"h{i}_score"].eval()))
    return hands


def onCook(scriptOp):  # noqa: N802 - TD entry point
    scriptOp.clear()
    machine, schedule = _state()

    hands = _read_hands(scriptOp.inputs[0] if scriptOp.inputs else None)
    now_ms = absTime.seconds * 1000.0  # noqa: F821

    observation = classify_hands(hands)
    snapshot = machine.update(observation, now_ms)
    schedule = advance_effect_schedule(schedule, snapshot, now_ms)
    me.store(_SCHEDULE_KEY, schedule)  # noqa: F821

    origin = snapshot.get("effectOrigin")
    left = snapshot.get("leftIndex")
    right = snapshot.get("rightIndex")
    spawn = schedule["spawn"]

    scriptOp.appendChan("kind_index")[0] = KIND_TO_INDEX[snapshot["stableKind"]]
    scriptOp.appendChan("confidence")[0] = snapshot.get("confidence", 0.0)
    scriptOp.appendChan("changed")[0] = 1 if snapshot["changed"] else 0

    scriptOp.appendChan("origin_x")[0] = origin.x if origin else 0.5
    scriptOp.appendChan("origin_y")[0] = origin.y if origin else 0.5

    scriptOp.appendChan("left_valid")[0] = 1 if left else 0
    scriptOp.appendChan("left_x")[0] = left.x if left else 0.5
    scriptOp.appendChan("left_y")[0] = left.y if left else 0.5

    scriptOp.appendChan("right_valid")[0] = 1 if right else 0
    scriptOp.appendChan("right_x")[0] = right.x if right else 0.5
    scriptOp.appendChan("right_y")[0] = right.y if right else 0.5

    scriptOp.appendChan("fire_small")[0] = 1 if "small" in spawn else 0
    scriptOp.appendChan("fire_strong")[0] = 1 if "strong" in spawn else 0
    scriptOp.appendChan("beam")[0] = 1 if schedule["beamBurst"] else 0
    scriptOp.appendChan("shockwave")[0] = 1 if schedule["shockwave"] else 0
