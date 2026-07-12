"""150ms stabilization / 300ms release state machine — a port of machine.ts.

`update(observation, now_ms)` returns a snapshot dict extending the observation
with `stableKind`, `enteredAtMs`, and `changed`.
"""

from __future__ import annotations

ENTER_DELAY_MS = 150
RELEASE_DURATION_MS = 300


class GestureMachine:
    def __init__(self):
        self.reset()

    def reset(self):
        self._candidate_kind = None
        self._candidate_since = 0
        self._stable_kind = "idle"
        self._entered_at = 0
        self._release_since = None

    def update(self, observation: dict, now_ms: float) -> dict:
        changed = False
        kind = observation["kind"]

        if kind == "idle":
            self._candidate_kind = None
            if self._stable_kind not in ("idle", "releasing"):
                self._stable_kind = "releasing"
                self._release_since = now_ms
                self._entered_at = now_ms
                changed = True
            elif (
                self._stable_kind == "releasing"
                and self._release_since is not None
                and now_ms - self._release_since >= RELEASE_DURATION_MS
            ):
                self._stable_kind = "idle"
                self._release_since = None
                self._entered_at = now_ms
                changed = True
        elif self._candidate_kind != kind:
            self._candidate_kind = kind
            self._candidate_since = now_ms
        elif (
            self._stable_kind != kind
            and now_ms - self._candidate_since >= ENTER_DELAY_MS
        ):
            self._stable_kind = kind
            self._entered_at = now_ms
            self._release_since = None
            changed = True

        snapshot = dict(observation)
        snapshot["stableKind"] = self._stable_kind
        snapshot["enteredAtMs"] = self._entered_at
        snapshot["changed"] = changed
        return snapshot
