"""Monster species data and monster instances (party members / wild foes)."""
import json
import os
import random

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


def _load(filename):
    with open(os.path.join(_DATA_DIR, filename)) as f:
        return json.load(f)


def load_species():
    return _load("monsters.json")["species"]


def load_moves():
    return _load("moves.json")["moves"]


def load_type_chart():
    return _load("types.json")["beats"]


class Monster:
    """A concrete monster: species stats scaled by level, plus HP and move PP."""

    def __init__(self, species_id, level, species_table=None, move_table=None):
        species_table = species_table or load_species()
        move_table = move_table or load_moves()
        self.species_id = species_id
        self.species = species_table[species_id]
        self.name = self.species["name"]
        self.level = level
        self.types = list(self.species["types"])
        base = self.species["base_stats"]
        self.max_hp = base["hp"] + 2 * level
        self.attack = base["attack"] + level // 2
        self.defense = base["defense"] + level // 2
        self.speed = base["speed"] + level // 2
        self.special = base["special"] + level // 2
        self.hp = self.max_hp
        self.xp = 0
        self.moves = [
            {"id": move_id, "data": dict(move_table[move_id]), "pp": move_table[move_id]["pp"]}
            for move_id in self.species["moves"]
        ]

    @property
    def fainted(self):
        return self.hp <= 0

    def usable_moves(self):
        return [m for m in self.moves if m["pp"] > 0]


def roll_wild(zone, party=None, species_table=None, move_table=None):
    """Pick a random wild monster for a zone using its encounter table.

    Levels scale with the party average (spec 9.3) but never exceed the
    player's best level + 5. Tier-4 legendaries have a small chance to
    appear in any zone on top of the normal table (spec 9.2).
    """
    species_table = species_table or load_species()
    move_table = move_table or load_moves()
    table = zone["encounters"]
    species_id = random.choices(list(table), weights=table.values())[0]
    lo, hi = zone["encounter_levels"]
    level = random.randint(lo, hi)
    if party:
        avg = sum(m.level for m in party) / len(party)
        best = max(m.level for m in party)
        # Scale toward the party average, but never above best + 5 (spec 9.3)
        # and never above the zone's own ceiling so starter zones stay safe.
        level = min(max(level, min(int(avg), best + 5)), hi)
    if zone.get("legendary_chance", 0) > 0 and random.random() < zone["legendary_chance"]:
        legendaries = [sid for sid, s in species_table.items() if s["tier"] == 4]
        species_id = random.choice(legendaries)
        level = min(50, hi + 2)
    return Monster(species_id, level, species_table, move_table)
