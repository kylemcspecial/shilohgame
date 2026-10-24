"""Random encounter triggering for tall-grass steps."""
import random


class EncounterTracker:
    """Decides when a step in tall grass starts a wild battle."""

    def __init__(self, rate=0.125):
        self.rate = rate
        self._rng = random

    def should_trigger(self):
        return self._rng.random() < self.rate
