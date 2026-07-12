"""Shared domain types for the TouchDesigner gesture pipeline."""

from __future__ import annotations

from collections import namedtuple

# handedness: "Left" | "Right"; landmarks: list[Vec3] (21); score: float
HandSample = namedtuple("HandSample", ["handedness", "landmarks", "score"])

# Stable gesture kinds, matching the web app's GestureKind union.
GESTURE_KINDS = (
    "idle",
    "egg-ready",
    "lock-ready",
    "both-ready",
    "fusing",
    "armed",
    "finger-heart",
    "big-heart",
    "releasing",
)

# Numeric encoding so a stable kind can travel on a CHOP channel.
KIND_TO_INDEX = {kind: index for index, kind in enumerate(GESTURE_KINDS)}
INDEX_TO_KIND = {index: kind for kind, index in KIND_TO_INDEX.items()}
