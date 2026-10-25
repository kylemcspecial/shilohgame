"""Experience, leveling, and move learning."""
import random

LEVEL_CAP = 50

_XP_FORMULA_BASE = 8


def xp_for_defeat(defeated_level, defeated_tier, victor_level=None):
    """XP from a defeat, scaled by rarity and the victor's level gap.

    Fighting foes far below your level pays little: 50% at 5+ below,
    25% at 10+ below, and 10% at 15+ below. Grinding easy zones
    no longer levels you; fighting up stays fully rewarding.
    """
    base = int(_XP_FORMULA_BASE * defeated_level * (1.0 + 0.25 * (defeated_tier - 1)))
    if victor_level is None:
        return base
    gap = victor_level - defeated_level
    if gap >= 15:
        return max(1, base // 10)
    if gap >= 10:
        return base // 4
    if gap >= 5:
        return base // 2
    return base


def xp_to_next(level):
    """Superlinear XP needed to advance: early levels quick, later ones earned."""
    return 10 + 5 * level + (level * level) // 4


def grant_xp(monster, amount, rng=None):
    """Add XP; returns a list of event dicts, e.g. level ups and learned moves."""
    rng = rng or random
    events = []
    monster.xp = getattr(monster, "xp", 0) + amount
    messages = []
    while monster.level < LEVEL_CAP and monster.xp >= xp_to_next(monster.level):
        monster.xp -= xp_to_next(monster.level)
        _level_up(monster)
        events.append({"type": "level_up", "level": monster.level})
        learned = _learn_move_at_level(monster)
        if learned:
            events.append({"type": "learned_move", "move": learned})
        evolved = check_evolution(monster)
        if evolved is not None:
            events.append({"type": "evolved", "from": monster.species_id, "to": evolved})
    return events


def check_evolution(monster, species_table=None):
    """Evolve at the species' set level. Returns the new species id or None.

    The monster instance is mutated in place: species, name, types, and stats
    are rebuilt at the new form while keeping HP ratio and known moves.
    """
    evo = monster.species.get("evolve_into")
    if not evo or monster.level < evo["level"]:
        return None
    from ..monsters.monster import Monster, load_species, load_moves

    species_table = species_table or load_species()
    old_name = monster.name
    hp_ratio = monster.hp / monster.max_hp if monster.max_hp else 1.0
    moves = monster.moves
    xp = getattr(monster, "xp", 0)

    new_mon = Monster(evo["species"], monster.level, species_table, load_moves())
    if getattr(monster, "shiny", False):
        # shininess survives evolution: boost the new form, then restore ratio
        new_mon.make_shiny()
    new_mon.hp = max(1, int(new_mon.max_hp * hp_ratio))
    new_mon.moves = moves
    new_mon.xp = xp
    monster.__dict__.update(new_mon.__dict__)
    monster.brace_stacks = 0
    monster.pre_evolution_name = old_name
    return evo["species"]


def _level_up(monster):
    monster.level += 1
    shiny = bool(getattr(monster, "shiny", False))
    old_max = monster.max_hp
    monster.max_hp = monster.species["base_stats"]["hp"] + 2 * monster.level
    monster.attack = monster.species["base_stats"]["attack"] + monster.level // 2
    monster.defense = monster.species["base_stats"]["defense"] + monster.level // 2
    monster.brace_stacks = 0
    monster.speed = monster.species["base_stats"]["speed"] + monster.level // 2
    monster.special = monster.species["base_stats"]["special"] + monster.level // 2
    if shiny:
        # re-apply the shiny boost on the rebuilt stats BEFORE the HP gain,
        # so max comparisons stay consistent (old_max was also boosted)
        monster.max_hp = int(monster.max_hp * 1.1)
        monster.attack = int(monster.attack * 1.1)
        monster.defense = int(monster.defense * 1.1)
        monster.speed = int(monster.speed * 1.1)
    monster.hp = min(monster.max_hp, monster.hp + (monster.max_hp - old_max))


def _learn_move_at_level(monster):
    pool = monster.species.get("move_pool", {})
    new_moves = [
        (lvl, mid) for lvl, mid in pool.items() if int(lvl) == monster.level
    ]
    if not new_moves:
        return None
    move_id = new_moves[0][1]
    if move_id in [m["id"] for m in monster.moves]:
        return None
    from ..monsters.monster import load_moves
    move_table = load_moves()
    if len(monster.moves) < 4:
        monster.moves.append(
            {"id": move_id, "data": dict(move_table[move_id]), "pp": move_table[move_id]["pp"]}
        )
        return move_id
    return None  # forget-choice handled by caller when 4 moves are known
