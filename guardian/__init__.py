"""Guardian Heart gesture core — TouchDesigner-independent, unit-tested logic.

Mirrors the web app's tested modules so the TD build reacts to gestures exactly
like the browser version.
"""

from .classify import classify_hands
from .effect_schedule import advance_effect_schedule, create_effect_schedule
from .geometry import Vec3, vec3
from .machine import GestureMachine
from .types import HandSample, INDEX_TO_KIND, KIND_TO_INDEX

__all__ = [
    "classify_hands",
    "advance_effect_schedule",
    "create_effect_schedule",
    "Vec3",
    "vec3",
    "GestureMachine",
    "HandSample",
    "INDEX_TO_KIND",
    "KIND_TO_INDEX",
]
