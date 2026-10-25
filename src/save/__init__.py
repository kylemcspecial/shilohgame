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
        "player_name": getattr(world, "player_name", "Hunter"),
        "rival_name": getattr(world, "rival_name", "Emmett"),
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
        "puzzle_state": getattr(world, "puzzles", None).serialize()
        if getattr(world, "puzzles", None) else {},
        "berry_patches": {
            f"{zid}:{x}:{y}": t for (zid, x, y), t in
            getattr(world, "berry_patches", {}).items()
        },
    }


def _serialize_monster(m):
    return {
        "species_id": m.species_id,
        "level": m.level,
        "xp": getattr(m, "xp", 0),
        "hp": m.hp,
        "moves": [{"id": mv["id"], "pp": mv["pp"]} for mv in m.moves],
        "shiny": bool(getattr(m, "shiny", False)),
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
    from ..monsters.monster import load_species, load_moves
    from ..world.scene import load_zones

    species, moves = load_species(), load_moves()
    if data["zone_id"] not in load_zones()["zones"]:
        raise ValueError("zone_id")
    for entry in data["party"] + data.get("storage", []):
        if not isinstance(entry, dict):
            raise TypeError("monster entry")
        if entry.get("species_id") not in species:
            raise ValueError("species_id")
        if not isinstance(entry.get("level", 0), int) or entry["level"] < 1:
            raise ValueError("level")
        for mv in entry.get("moves", []):
            if not isinstance(mv, dict) or mv.get("id") not in moves:
                raise ValueError("move id")


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
    saved_moves = entry.get("moves")
    if saved_moves:
        # Rebuild the moveset from saved IDs so learned moves survive loading.
        restored = []
        for saved in saved_moves:
            move_id = saved["id"]
            if move_id not in move_table:
                continue
            fresh = dict(move_table[move_id])
            restored.append({
                "id": move_id,
                "data": fresh,
                "pp": max(0, min(saved.get("pp", fresh["pp"]), fresh["pp"])),
            })
        if restored:
            mon.moves = restored
    if entry.get("shiny"):
        mon.make_shiny()
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
    world.player_name = data.get("player_name", "Hunter")
    world.rival_name = data.get("rival_name", "Emmett")
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
    puzzles = getattr(world, "puzzles", None)
    if puzzles is not None:
        puzzles.state = data.get("puzzle_state", {}) or {}
        world._init_puzzle_state()
    patches = getattr(world, "berry_patches", None)
    if patches is not None:
        world.berry_patches = {}
        for k, t in (data.get("berry_patches", {}) or {}).items():
            zid, x, y = k.split(":", 2)
            world.berry_patches[(zid, int(x), int(y))] = t
