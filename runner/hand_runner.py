"""External MediaPipe sensor: webcam -> gestures -> OSC to TouchDesigner.

On macOS, TouchDesigner's bundled Python is a hardened runtime that refuses to
load pip-installed native extensions (MediaPipe, matplotlib) — "different Team
IDs". So MediaPipe runs here, in a normal venv, and only the resulting gesture
data crosses into TD over OSC. TD needs just an `OSC In CHOP` (no packages).

Run (from the project folder):

    .venv/bin/python runner/hand_runner.py               # camera 0, OSC 127.0.0.1:7000
    .venv/bin/python runner/hand_runner.py --preview     # + a local landmark window
    .venv/bin/python runner/hand_runner.py --selftest    # no camera; emit one fixture frame

Each frame sends one OSC message per channel, so TD's OSC In CHOP produces
cleanly named channels (kind_index, left_x, fire_small, ...).
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Make the sibling `guardian` package importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardian.classify import classify_hands  # noqa: E402
from guardian.effect_schedule import (  # noqa: E402
    advance_effect_schedule,
    create_effect_schedule,
)
from guardian.geometry import vec3  # noqa: E402
from guardian.machine import GestureMachine  # noqa: E402
from guardian.types import HandSample, KIND_TO_INDEX  # noqa: E402

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models",
    "hand_landmarker.task",
)


def _channels(snapshot: dict, schedule: dict) -> dict:
    origin = snapshot.get("effectOrigin")
    left = snapshot.get("leftIndex")
    right = snapshot.get("rightIndex")
    spawn = schedule["spawn"]
    return {
        "kind_index": KIND_TO_INDEX[snapshot["stableKind"]],
        "confidence": float(snapshot.get("confidence", 0.0)),
        "changed": 1 if snapshot["changed"] else 0,
        "origin_x": origin.x if origin else 0.5,
        "origin_y": origin.y if origin else 0.5,
        "left_valid": 1 if left else 0,
        "left_x": left.x if left else 0.5,
        "left_y": left.y if left else 0.5,
        "right_valid": 1 if right else 0,
        "right_x": right.x if right else 0.5,
        "right_y": right.y if right else 0.5,
        "fire_small": 1 if "small" in spawn else 0,
        "fire_strong": 1 if "strong" in spawn else 0,
        "beam": 1 if schedule["beamBurst"] else 0,
        "shockwave": 1 if schedule["shockwave"] else 0,
    }


def _make_sender(host: str, port: int):
    from pythonosc.udp_client import SimpleUDPClient

    client = SimpleUDPClient(host, port)

    def send(channels: dict):
        for name, value in channels.items():
            client.send_message("/" + name, value)

    return send


def _hand_samples(result):
    hands = []
    landmark_sets = result.hand_landmarks or []
    handedness = result.handedness or []
    for i, landmarks in enumerate(landmark_sets):
        category = handedness[i][0] if i < len(handedness) else None
        name = category.category_name if category else "Right"
        score = category.score if category else 0.0
        points = [vec3(lm.x, lm.y, lm.z) for lm in landmarks]
        hands.append(HandSample(name, points, score))
    return hands


def run_selftest(send):
    """Emit one synthetic big-heart frame — verifies the pipeline without a camera."""
    machine = GestureMachine()
    schedule = create_effect_schedule()

    def hand(center_x, tips):
        pts = [vec3(center_x, -0.6) for _ in range(21)]
        pts[0] = vec3(center_x, 0)
        pts[9] = vec3(center_x, -1)
        for idx, point in tips.items():
            pts[idx] = point
        return HandSample("Left" if center_x < 0 else "Right", pts, 0.99)

    big_heart = [
        hand(-1, {4: vec3(-0.12, -1), 8: vec3(-0.12, -3)}),
        hand(1, {4: vec3(0.12, -1), 8: vec3(0.12, -3)}),
    ]
    # Hold the pose past the 150ms stabilization so it actually commits and fires.
    machine.update(classify_hands(big_heart), 0.0)
    snapshot = machine.update(classify_hands(big_heart), 160.0)
    schedule = advance_effect_schedule(schedule, snapshot, 160.0)
    channels = _channels(snapshot, schedule)
    send(channels)
    print("selftest sent:", channels)


def run_camera(send, camera_index: int, preview: bool):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    options = mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=mp_vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.55,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = mp_vision.HandLandmarker.create_from_options(options)

    capture = cv2.VideoCapture(camera_index)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not capture.isOpened():
        raise SystemExit(f"Could not open camera {camera_index}.")

    machine = GestureMachine()
    schedule = create_effect_schedule()
    start = time.perf_counter()
    print("hand_runner streaming OSC. Ctrl+C to stop.", flush=True)

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                continue
            now_ms = (time.perf_counter() - start) * 1000.0
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(image, int(now_ms))

            hands = _hand_samples(result)
            snapshot = machine.update(classify_hands(hands), now_ms)
            schedule = advance_effect_schedule(schedule, snapshot, now_ms)
            send(_channels(snapshot, schedule))

            if preview:
                view = cv2.flip(frame, 1)  # mirror for comfort (display only)
                cv2.putText(
                    view,
                    snapshot["stableKind"],
                    (24, 48),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.1,
                    (124, 245, 210),
                    2,
                    cv2.LINE_AA,
                )
                for hand in hands:
                    for point in hand.landmarks:
                        cx = int((1.0 - point.x) * view.shape[1])
                        cy = int(point.y * view.shape[0])
                        cv2.circle(view, (cx, cy), 3, (255, 92, 158), -1)
                cv2.imshow("Guardian Heart — hand runner", view)
                if cv2.waitKey(1) & 0xFF == 27:  # Esc
                    break
    except KeyboardInterrupt:
        pass
    finally:
        capture.release()
        if preview:
            cv2.destroyAllWindows()
        landmarker.close()


def main():
    parser = argparse.ArgumentParser(description="Guardian Heart MediaPipe -> OSC runner")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7000)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    send = _make_sender(args.host, args.port)
    if args.selftest:
        run_selftest(send)
    else:
        run_camera(send, args.camera, args.preview)


if __name__ == "__main__":
    main()
