"""Pure emission timing — a port of effectSchedule.ts.

Small hearts stream every 250ms while a finger heart is held; strong hearts
pulse every 900ms while a big heart is held. Entry-only beam/shockwave flags
fire once per pose entry; nothing spawns while releasing.
"""

from __future__ import annotations

SMALL_INTERVAL_MS = 250
STRONG_INTERVAL_MS = 900


def create_effect_schedule() -> dict:
    return {
        "beamBurst": False,
        "shockwave": False,
        "spawn": [],
        "lastSmallMs": float("-inf"),
        "lastStrongMs": float("-inf"),
    }


def advance_effect_schedule(previous: dict, snapshot: dict, now_ms: float) -> dict:
    kind = snapshot["stableKind"]
    spawn = []
    last_small = previous["lastSmallMs"]
    last_strong = previous["lastStrongMs"]
    beam_burst = False
    shockwave = False

    if kind == "finger-heart":
        if snapshot["changed"] or now_ms - last_small >= SMALL_INTERVAL_MS:
            spawn.append("small")
            last_small = now_ms
        if snapshot["changed"]:
            beam_burst = True
    elif kind == "big-heart":
        if snapshot["changed"] or now_ms - last_strong >= STRONG_INTERVAL_MS:
            spawn.append("strong")
            last_strong = now_ms
        if snapshot["changed"]:
            beam_burst = True
            shockwave = True

    return {
        "beamBurst": beam_burst,
        "shockwave": shockwave,
        "spawn": spawn,
        "lastSmallMs": last_small,
        "lastStrongMs": last_strong,
    }
