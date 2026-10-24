"""Trainers: NPC placement, challenge triggers, defeat flags, cooldowns."""
import json
import os
import time

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
REBATTLE_COOLDOWN = 300.0  # seconds; trainers can be battled again after this


def load_trainers():
    with open(os.path.join(_DATA_DIR, "trainers.json")) as f:
        return json.load(f)


class TrainerState:
    """Tracks defeat flags and rebattle cooldowns for the run."""

    def __init__(self):
        self.defeated = {}
        self.last_battled = {}

    def can_challenge(self, trainer_id, trainer):
        if trainer.get("requires_defeat") and not self.defeated.get(trainer["requires_defeat"]):
            return False
        if not self.defeated.get(trainer_id):
            return True  # never beaten them; always allow
        last = self.last_battled.get(trainer_id)
        if last is None:
            # Defeated but no timer (e.g. restored from an older save):
            # start the cooldown now rather than allowing an instant rematch.
            self.last_battled[trainer_id] = self._now()
            return False
        return (self._now() - last) >= REBATTLE_COOLDOWN

    def record_win(self, trainer_id):
        self.defeated[trainer_id] = True
        self.last_battled[trainer_id] = self._now()

    def record_start(self, trainer_id):
        self.last_battled[trainer_id] = self._now()

    @staticmethod
    def _now():
        """Wall clock so persisted cooldowns stay valid across reboots."""
        return time.time()


def trainers_in_zone(zone_id):
    data = load_trainers()
    return [
        (tid, t) for tid, t in data["trainers"].items() if t["zone"] == zone_id
    ]
