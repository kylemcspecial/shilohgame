"""Turn-based battle logic: damage, turn order, running."""
import random


SUPER_EFFECTIVE = 2.0
NOT_VERY_EFFECTIVE = 0.5


def type_multiplier(move_type, target_types, type_chart):
    """Spec chart: attacker type beats listed defender types (2x). Neutral otherwise."""
    multiplier = 1.0
    for target_type in target_types:
        if target_type in type_chart.get(move_type, []):
            multiplier *= SUPER_EFFECTIVE
    return multiplier


def damage(attacker, defender, move, type_chart, rng=None):
    """Simplified spec formula, returned as an integer >= 1."""
    rng = rng or random
    base = ((2 * attacker.level / 5 + 2) * move["power"] * attacker.attack / defender.defense) / 50 + 2
    multiplier = type_multiplier(move["type"], defender.types, type_chart)
    roll = rng.uniform(0.85, 1.0)
    return max(1, int(base * multiplier * roll)), multiplier


def effectiveness_text(multiplier):
    if multiplier > 1.0:
        return "It's super effective!"
    if multiplier < 1.0:
        return "It's not very effective..."
    return ""


def goes_first(player_mon, enemy_mon, rng=None):
    """Higher speed first; ties broken randomly."""
    rng = rng or random
    if player_mon.speed == enemy_mon.speed:
        return rng.random() < 0.5
    return player_mon.speed > enemy_mon.speed


def run_chance(player_mon, enemy_mon, rng=None):
    """Run succeeds based on speed comparison plus a random roll."""
    rng = rng or random
    if player_mon.speed >= enemy_mon.speed:
        return True
    return rng.random() < player_mon.speed / enemy_mon.speed


def apply_move(attacker, defender, move_entry, type_chart, rng=None):
    """Execute one offensive or defensive move. Returns (events, messages)."""
    rng = rng or random
    move = move_entry["data"]
    move_entry["pp"] = max(0, move_entry["pp"] - 1)
    events = []
    messages = []

    if rng.randint(1, 100) > move["accuracy"]:
        events.append("missed")
        messages.append(f"{attacker.name}'s attack missed!")
        return events, messages

    if move["category"] == "defensive":
        if move["effect"] == "raise_defense":
            stacks = int(getattr(attacker, "brace_stacks", 0))
            if stacks >= 2:
                messages.append(f"{attacker.name} is already braced!")
            else:
                attacker.brace_stacks = stacks + 1
                attacker.defense += max(1, attacker.level // 2 + 1)
                events.append("defense_up")
                messages.append(f"{attacker.name} braced for impact!")
        return events, messages

    dealt, multiplier = damage(attacker, defender, move, type_chart, rng)
    defender.hp = max(0, defender.hp - dealt)
    events.append("damage")
    messages.append(f"{attacker.name} used {move['name']}! {defender.name} took {dealt} damage.")
    text = effectiveness_text(multiplier)
    if text:
        messages.append(text)
    if defender.fainted:
        events.append("fainted")
    return events, messages
