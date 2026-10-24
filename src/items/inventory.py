"""Item data and the player's inventory (counts by item id)."""
import json
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


def load_items():
    with open(os.path.join(_DATA_DIR, "items.json")) as f:
        return json.load(f)["items"]


class Inventory:
    """Counts of each item id; traps and consumables both live here."""

    def __init__(self, initial=None):
        self.items = load_items()
        self.counts = dict(initial or {})

    def add(self, item_id, n=1):
        self.counts[item_id] = self.counts.get(item_id, 0) + n

    def remove(self, item_id, n=1):
        if self.counts.get(item_id, 0) < n:
            return False
        self.counts[item_id] -= n
        if self.counts[item_id] == 0:
            del self.counts[item_id]
        return True

    def count(self, item_id):
        return self.counts.get(item_id, 0)

    def traps(self):
        return [(iid, d) for iid, d in self.items.items()
                if d["kind"] == "trap" and self.counts.get(iid, 0) > 0]

    def name(self, item_id):
        return self.items[item_id]["name"]
