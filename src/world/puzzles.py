"""Zone puzzles (M10): boulders, stepping stones, riddles, lanterns.

Each puzzle is a small state machine persisted in the save dict under
`puzzle_state`. Solved puzzles stay solved; unsolved ones can be reset.

Data-driven: puzzle definitions live in zones.json under `puzzles`.
"""
import json
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")

_SOLID = ("T", "#", "H", "S", "B")


def load_puzzle_defs():
    """All puzzle definitions keyed by zone id."""
    with open(os.path.join(_DATA_DIR, "zones.json")) as f:
        return json.load(f)["zones"]


class ZonePuzzles:
    """Tracks puzzle progress for the whole run, one puzzle per zone."""

    def __init__(self, state=None):
        # {"boulder": {"solved": True, ...}, ...} keyed by puzzle id
        self.state = dict(state or {})

    def solved(self, puzzle_id):
        return self.state.get(puzzle_id, {}).get("solved", False)

    def mark_solved(self, puzzle_id):
        entry = self.state.setdefault(puzzle_id, {})
        entry["solved"] = True

    def reset(self, puzzle_id):
        self.state.pop(puzzle_id, None)

    def get(self, puzzle_id, key, default=None):
        return self.state.get(puzzle_id, {}).get(key, default)

    def set(self, puzzle_id, key, value):
        self.state.setdefault(puzzle_id, {})[key] = value

    def serialize(self):
        return {pid: dict(data) for pid, data in self.state.items()}


# --------------------------------------------------------------- boulder

def boulder_push(boulders, switches, dx, dy, boulder_pos):
    """Try to push a boulder one tile; returns new position or None."""
    bx, by = boulder_pos
    nx, ny = bx + dx, by + dy
    if (nx, ny) in boulders:
        return None  # another boulder in the way
    return (nx, ny)


def boulder_solved(boulders, switches):
    """Solved when every switch tile has a boulder on it."""
    return all(s in boulders for s in switches)


# ---------------------------------------------------------- stepping stones

def stones_step(sequence, entered, tile):
    """Enter a stone tile; returns (ok, new_entered). Wrong tile resets."""
    if tile == sequence[len(entered)]:
        return True, entered + [tile]
    return False, []


def stones_solved(sequence, entered):
    return len(entered) >= len(sequence)


# ----------------------------------------------------------------- riddles

def riddle_answered(state, riddle_id, choice, correct):
    """Record a riddle answer; returns True if correct."""
    ok = choice == correct
    state.setdefault("answers", {})[riddle_id] = ok
    return ok


def riddles_solved(state, riddle_ids):
    answers = state.get("answers", {})
    return all(answers.get(rid) for rid in riddle_ids)


# ---------------------------------------------------------------- lanterns

def lantern_toggle(lanterns_on, index, layout):
    """Toggle a lantern and its grid neighbors (classic lights-out)."""
    for i in layout[index]:
        lanterns_on[i] = not lanterns_on[i]
    return lanterns_on


def lanterns_solved(lanterns_on):
    return all(lanterns_on)
