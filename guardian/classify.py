"""Stateless hand-pose classification — a faithful port of classify.ts.

Returns an observation dict:
    {kind, leftIndex?, rightIndex?, effectOrigin?, confidence}
where the optional points are Vec3 in normalized MediaPipe coordinates.
"""

from __future__ import annotations

from .geometry import Vec3, midpoint, normalized_distance, palm_scale

THUMB_TIP = 4
INDEX_TIP = 8
OTHER_FINGERTIPS = (12, 16, 20)


def _confidence_of(hands) -> float:
    return min(hand.score for hand in hands)


def _center_of(points) -> Vec3:
    count = len(points)
    return Vec3(
        sum(p.x for p in points) / count,
        sum(p.y for p in points) / count,
        sum(p.z for p in points) / count,
    )


def _is_index_only(hand) -> bool:
    scale = palm_scale(hand.landmarks)
    wrist = hand.landmarks[0]
    return normalized_distance(hand.landmarks[INDEX_TIP], wrist, scale) > 1.6 and all(
        normalized_distance(hand.landmarks[index], wrist, scale) < 1.25
        for index in OTHER_FINGERTIPS
    )


def _heart_observation(kind, left, right) -> dict:
    left_index = left.landmarks[INDEX_TIP]
    right_index = right.landmarks[INDEX_TIP]
    return {
        "kind": kind,
        "leftIndex": left_index,
        "rightIndex": right_index,
        "effectOrigin": midpoint(left_index, right_index),
        "confidence": _confidence_of([left, right]),
    }


def classify_hands(hands) -> dict:
    visible = sorted(
        (hand for hand in hands if len(hand.landmarks) >= 21),
        key=lambda hand: hand.landmarks[INDEX_TIP].x,
    )

    if len(visible) >= 2:
        left, right = visible[0], visible[1]
        scale = (palm_scale(left.landmarks) + palm_scale(right.landmarks)) / 2
        left_thumb = left.landmarks[THUMB_TIP]
        right_thumb = right.landmarks[THUMB_TIP]
        left_index = left.landmarks[INDEX_TIP]
        right_index = right.landmarks[INDEX_TIP]
        thumb_gap = normalized_distance(left_thumb, right_thumb, scale)
        index_gap = normalized_distance(left_index, right_index, scale)
        left_span = normalized_distance(left_thumb, left_index, scale)
        right_span = normalized_distance(right_thumb, right_index, scale)

        is_large_heart = (
            thumb_gap < 0.55
            and index_gap < 0.55
            and left_span > 1.2
            and right_span > 1.2
            and abs(left_span - right_span) < 0.5
        )
        if is_large_heart:
            return _heart_observation("big-heart", left, right)

        is_compact_heart = (
            left_span < 0.4
            and right_span < 0.4
            and normalized_distance(
                midpoint(left_thumb, left_index),
                midpoint(right_thumb, right_index),
                scale,
            )
            < 0.75
        )
        if is_compact_heart:
            return _heart_observation("finger-heart", left, right)

    summons = [hand for hand in visible if _is_index_only(hand)]

    if len(summons) >= 2:
        left = summons[0]
        right = summons[-1]
        left_index = left.landmarks[INDEX_TIP]
        right_index = right.landmarks[INDEX_TIP]
        return {
            "kind": "both-ready",
            "leftIndex": left_index,
            "rightIndex": right_index,
            "effectOrigin": midpoint(left_index, right_index),
            "confidence": _confidence_of([left, right]),
        }

    if len(summons) == 1:
        hand = summons[0]
        index = hand.landmarks[INDEX_TIP]
        is_screen_left = index.x < 0.5
        observation = {
            "kind": "egg-ready" if is_screen_left else "lock-ready",
            "effectOrigin": _center_of([index]),
            "confidence": hand.score,
        }
        if is_screen_left:
            observation["leftIndex"] = index
        else:
            observation["rightIndex"] = index
        return observation

    return {"kind": "idle", "confidence": 0}
