"""Normalized landmark geometry — a faithful port of the web app's geometry.ts.

Pure functions with no TouchDesigner dependency, so they are unit-testable with
plain CPython and behave identically to the tested TypeScript originals.
"""

from __future__ import annotations

import math
from collections import namedtuple

Vec3 = namedtuple("Vec3", ["x", "y", "z"])


def vec3(x: float, y: float, z: float = 0.0) -> Vec3:
    return Vec3(float(x), float(y), float(z))


def distance(a: Vec3, b: Vec3) -> float:
    return math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)


def midpoint(a: Vec3, b: Vec3) -> Vec3:
    return Vec3((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)


def palm_scale(landmarks) -> float:
    return max(distance(landmarks[0], landmarks[9]), 0.001)


def normalized_distance(a: Vec3, b: Vec3, scale: float) -> float:
    return distance(a, b) / scale
