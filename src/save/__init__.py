"""Save/load: three JSON slots in a user data directory, with corruption handling."""
import json
import os

SLOT_COUNT = 3

_VERSION = 1


def save_dir():
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    path = os.path.join(base, "fierce-monster-hunter", "saves")
    os.makedirs(path, exist_ok=True)
    return path


def slot_path(slot):
    return os.path.join(save_dir(), f"slot{slot}.json")


def serialize(world):
    """Convert a WorldScene into a JSON-safe dict."""
    return {
        "version": _VERSION,
        "zone_id": world.zone_id,
        "player": {"tile_x": world.player.tile_x, "tile_y": world.player.tile_y},
        "coins": world.coins,
        "battles_won": world.battles_won,
        "monsters_caught": world.monsters_caught,
        "play_time": round(world.play_time, 1),
        "party": [_serialize_monster(m) for m in world.party],
        "storage": [_serialize_monster(m) for m in world.storage],
        "inventory": dict(world.inventory.counts),
        "trainer_defeated": dict(getattr(world.trainer_state, "defeated", {})),
        "trainer_last_battled": {
            k: v for k, v in getattr(world.trainer_state, "last_battled", {}).items()
        },
    }


def _serialize_monster(m):
    return {
        "species_id": m.species_id,
        "level": m.level,
        "xp": getattr(m, "xp", 0),
        "hp": m.hp,
        "moves": [{"id": mv["id"], "pp": mv["pp"]} for mv in m.moves],
    }


def save_game(world, slot):
    with open(slot_path(slot), "w") as f:
        json.dump(serialize(world), f, indent=2)


def load_game(slot, monster_tables=None):
    """Load a slot. Returns a dict of primitives, or None if empty/corrupt."""
    path = slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        _validate(data)
        return data
    except (json.JSONDecodeError, OSError, KeyError, ValueError, TypeError):
        return None


def _validate(data):
    for key in ("version", "zone_id", "player", "party", "inventory"):
        if key not in data:
            raise KeyError(key)
    if not isinstance(data["party"], list):
        raise TypeError("party")
    if not isinstance(data["player"], dict):
        raise TypeError("player")
    if "tile_x" not in data["player"] or "tile_y" not in data["player"]:
        raise KeyError("player coords")


def restore_monsters(data, monster_tables=None):
    """Rebuild Monster objects from a loaded save dict."""
    from ..monsters.monster import Monster, load_species, load_moves
    species_table, move_table = monster_tables or (load_species(), load_moves())
    party = []
    for entry in data["party"]:
        party.append(_restore_monster(entry, species_table, move_table))
    storage = [_restore_monster(e, species_table, move_table) for e in data.get("storage", [])]
    return party, storage


def _restore_monster(entry, species_table, move_table):
    from ..monsters.monster import Monster

    mon = Monster(entry["species_id"], entry["level"], species_table, move_table)
    mon.xp = entry.get("xp", 0)
    for saved in entry.get("moves", []):
        for mv in mon.moves:
            if mv["id"] == saved["id"]:
                mv["pp"] = saved.get("pp", mv["pp"])
    mon.hp = min(mon.max_hp, max(0, entry.get("hp", mon.max_hp)))
    return mon


def apply_save(world, data):
    """Apply a loaded save dict onto a WorldScene (and its inventory)."""
    from ..items.inventory import Inventory

    from ..world.tiles import TileMap

    world.zone_id = data["zone_id"]
    world.tile_map = TileMap(world.zones[world.zone_id])
    world.player.tile_x = data["player"]["tile_x"]
    world.player.tile_y = data["player"]["tile_y"]
    from ..engine.constants import TILE_SIZE

    world.player.px = world.player.tile_x * TILE_SIZE
    world.player.py = world.player.tile_y * TILE_SIZE
    world.player.moving = False
    world.coins = data.get("coins", 0)
    world.battles_won = data.get("battles_won", 0)
    world.monsters_caught = data.get("monsters_caught", 0)
    world.play_time = data.get("play_time", 0.0)
    party, storage = restore_monsters(data)
    world.party = party if party else world.party
    world.storage = storage
    world.inventory = Inventory(data.get("inventory", {}))
    if hasattr(world, "trainer_state"):
        world.trainer_state.defeated = dict(data.get("trainer_defeated", {}))
        world.trainer_state.last_battled = dict(data.get("trainer_last_battled", {}))
