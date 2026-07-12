"""Script CHOP callback: webcam frames -> MediaPipe hand landmarks.

Wire this as the callback DAT of a `Script CHOP` that sits next to a
`Video Device In TOP` named `videoin` (CHOPs cannot take a TOP as an input, so
the frame is fetched by name, not via an input wire). It emits, per cook (one
sample):

    n_hands
    h{i}_valid, h{i}_score, h{i}_hand        (hand=0 Left, 1 Right)
    h{i}_lm{k}_x, h{i}_lm{k}_y, h{i}_lm{k}_z  for i in 0..1, k in 0..20

Coordinates are MediaPipe-normalized (x,y in 0..1, origin top-left) — the same
space the ported classifier expects, so no remapping is needed downstream.

Requires MediaPipe in TouchDesigner's Python (see README):
    "<TD>/bin/python" -m pip install mediapipe numpy
"""

import os

import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
except Exception as import_error:  # pragma: no cover - TD runtime only
    mp = None
    _IMPORT_ERROR = import_error
else:
    _IMPORT_ERROR = None

MAX_HANDS = 2
_STATE_KEY = "guardian_hand_landmarker"


def _model_path():
    # project.folder is the folder containing the .toe file.
    return os.path.join(project.folder, "models", "hand_landmarker.task")  # noqa: F821


def _landmarker():
    """Lazily build (and cache) the HandLandmarker on the owning operator."""
    existing = me.fetch(_STATE_KEY, None)  # noqa: F821
    if existing is not None:
        return existing

    base_options = mp_python.BaseOptions(model_asset_path=_model_path())
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_hands=MAX_HANDS,
        min_hand_detection_confidence=0.55,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = mp_vision.HandLandmarker.create_from_options(options)
    me.store(_STATE_KEY, landmarker)  # noqa: F821
    return landmarker


def _frame_rgb(top):
    """Return an HxWx3 uint8 RGB frame from a TOP, or None if unavailable."""
    if top is None:
        return None
    array = top.numpyArray(delayed=False)  # HxWx4 float32 RGBA, 0..1
    if array is None or array.size == 0:
        return None
    rgb = (array[:, :, :3] * 255.0).clip(0, 255).astype(np.uint8)
    # TOPs are bottom-up; flip to top-down so y matches MediaPipe's origin.
    return np.ascontiguousarray(np.flipud(rgb))


def onCook(scriptOp):  # noqa: N802 - TD entry point
    scriptOp.clear()

    if mp is None:
        scriptOp.appendChan("n_hands")[0] = 0
        debug("MediaPipe import failed:", _IMPORT_ERROR)  # noqa: F821
        return

    source = me.parent().op("videoin")  # noqa: F821 - sibling Video Device In TOP
    frame = _frame_rgb(source)
    if frame is None:
        scriptOp.appendChan("n_hands")[0] = 0
        return

    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    timestamp_ms = int(absTime.seconds * 1000)  # noqa: F821 - monotonic in play
    result = _landmarker().detect_for_video(image, timestamp_ms)

    hands = result.hand_landmarks or []
    handedness = result.handedness or []
    scriptOp.appendChan("n_hands")[0] = min(len(hands), MAX_HANDS)

    for i in range(MAX_HANDS):
        valid = i < len(hands)
        scriptOp.appendChan(f"h{i}_valid")[0] = 1 if valid else 0

        category = handedness[i][0] if valid and i < len(handedness) else None
        scriptOp.appendChan(f"h{i}_score")[0] = category.score if category else 0.0
        scriptOp.appendChan(f"h{i}_hand")[0] = (
            0 if (category and category.category_name == "Left") else 1
        )

        for k in range(21):
            landmark = hands[i][k] if valid else None
            scriptOp.appendChan(f"h{i}_lm{k}_x")[0] = landmark.x if landmark else 0.0
            scriptOp.appendChan(f"h{i}_lm{k}_y")[0] = landmark.y if landmark else 0.0
            scriptOp.appendChan(f"h{i}_lm{k}_z")[0] = landmark.z if landmark else 0.0
