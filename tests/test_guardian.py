"""Verifies the Python port matches the web app's tested behaviour.

Mirrors the assertions in the web app's classify.test.ts, machine.test.ts, and
effectSchedule.test.ts. Run with `python3 tests/test_guardian.py` (no pytest
required) or `pytest`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardian.classify import classify_hands  # noqa: E402
from guardian.effect_schedule import (  # noqa: E402
    advance_effect_schedule,
    create_effect_schedule,
)
from guardian.geometry import vec3  # noqa: E402
from guardian.machine import GestureMachine  # noqa: E402
from guardian.types import HandSample  # noqa: E402


# --- fixtures ported from tests/fixtures/hands.ts ---------------------------


def _hand(handedness, center_x, tips):
    landmarks = [vec3(center_x, -0.6) for _ in range(21)]
    landmarks[0] = vec3(center_x, 0)
    landmarks[9] = vec3(center_x, -1)
    for index in (4, 8, 12, 16, 20):
        landmarks[index] = tips.get(index, vec3(center_x, -0.6))
    return HandSample(handedness, landmarks, 0.99)


def left_index_only():
    return _hand("Left", -1, {8: vec3(-1, -2.4)})


def right_index_only():
    return _hand("Right", 1, {8: vec3(1, -2.4)})


def finger_heart():
    return [
        _hand("Left", -0.35, {4: vec3(-0.08, -1.7), 8: vec3(-0.18, -1.82)}),
        _hand("Right", 0.35, {4: vec3(0.08, -1.7), 8: vec3(0.18, -1.82)}),
    ]


def big_heart():
    return [
        _hand("Left", -1, {4: vec3(-0.12, -1), 8: vec3(-0.12, -3)}),
        _hand("Right", 1, {4: vec3(0.12, -1), 8: vec3(0.12, -3)}),
    ]


def _observation(kind):
    return {"kind": kind, "confidence": 1}


# --- classify ---------------------------------------------------------------


def test_classifies_screen_left_and_right_summons():
    assert classify_hands([left_index_only()])["kind"] == "egg-ready"
    assert classify_hands([right_index_only()])["kind"] == "lock-ready"
    assert (
        classify_hands([left_index_only(), right_index_only()])["kind"]
        == "both-ready"
    )


def test_prefers_big_heart_over_compact_heart():
    assert classify_hands(big_heart())["kind"] == "big-heart"
    assert classify_hands(finger_heart())["kind"] == "finger-heart"


def test_idle_when_no_rule_matches():
    assert classify_hands([])["kind"] == "idle"


# --- machine ----------------------------------------------------------------


def test_requires_150ms_then_fades_through_releasing_for_300ms():
    machine = GestureMachine()
    assert machine.update(_observation("finger-heart"), 0)["stableKind"] == "idle"
    assert machine.update(_observation("finger-heart"), 149)["stableKind"] == "idle"
    assert (
        machine.update(_observation("finger-heart"), 150)["stableKind"]
        == "finger-heart"
    )
    assert machine.update(_observation("idle"), 151)["stableKind"] == "releasing"
    assert machine.update(_observation("idle"), 450)["stableKind"] == "releasing"
    assert machine.update(_observation("idle"), 451)["stableKind"] == "idle"


# --- effect schedule --------------------------------------------------------


def _snapshot(stable_kind, changed):
    return {
        "kind": "idle" if stable_kind == "releasing" else stable_kind,
        "confidence": 1,
        "stableKind": stable_kind,
        "enteredAtMs": 0,
        "changed": changed,
    }


def test_emits_small_every_250ms_and_strong_every_900ms():
    schedule = create_effect_schedule()

    schedule = advance_effect_schedule(schedule, _snapshot("finger-heart", True), 0)
    assert schedule["beamBurst"] is True
    assert schedule["spawn"] == ["small"]

    schedule = advance_effect_schedule(schedule, _snapshot("finger-heart", False), 249)
    assert schedule["spawn"] == []

    schedule = advance_effect_schedule(schedule, _snapshot("finger-heart", False), 250)
    assert schedule["spawn"] == ["small"]

    schedule = advance_effect_schedule(schedule, _snapshot("big-heart", True), 300)
    assert schedule["spawn"] == ["strong"]
    assert schedule["shockwave"] is True


def test_stops_spawning_while_releasing():
    schedule = create_effect_schedule()
    schedule = advance_effect_schedule(schedule, _snapshot("finger-heart", True), 0)
    schedule = advance_effect_schedule(schedule, _snapshot("releasing", True), 400)
    assert schedule["spawn"] == []
    assert schedule["beamBurst"] is False


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"  ok  {test.__name__}")
        except AssertionError as error:
            failures += 1
            print(f"FAIL  {test.__name__}: {error}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
