"""Tests for evolution, the expanded roster, and endless-loop features."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.monsters.monster import Monster, load_species, load_moves, roll_wild
from src.monsters import leveling
from src.battle import battle as battle_mod
from src.battle.scene import BattleScene


class FakeAudio:
    def confirm(self): pass
    def hit(self): pass
    def faint(self): pass
    def catch_success(self): pass
    def catch_fail(self): pass
    def level_up(self): pass
    def heal(self): pass


class FakeGame:
    audio = FakeAudio()

    class world:
        party = []

    class input:
        pressed = set()
        held = set()


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


def test_roster_size():
    assert len(load_species()) >= 40


def test_all_species_valid():
    species, moves = load_species(), load_moves()
    for sid, s in species.items():
        assert s["name"] and 1 <= len(s["types"]) <= 2
        assert 1 <= s["tier"] <= 4
        for mv in s["moves"] + list(s["move_pool"].values()):
            assert mv in moves, (sid, mv)
        evo = s.get("evolve_into")
        if evo:
            assert evo["species"] in species
            assert evo["level"] > 1


def test_type_chart_full():
    chart = __import__("src.monsters.monster", fromlist=["load_type_chart"]).load_type_chart()
    for t in ("leaf", "ember", "water", "stone", "storm", "frost"):
        assert t in chart


def test_evolution_triggers_at_level():
    m = mon("fernpup", 17)
    result = leveling.check_evolution(m)
    assert result is None
    m = mon("fernpup", 18)
    result = leveling.check_evolution(m)
    assert result == "fernfox"
    assert m.name == "Fernfox"
    assert m.species_id == "fernfox"


def test_evolution_via_xp():
    m = mon("mossrat", 15)
    events = leveling.grant_xp(m, leveling.xp_to_next(15) + 1)
    assert any(e["type"] == "evolved" for e in events)
    assert m.species_id == "bramblerat"
    assert m.hp > 0


def test_evolution_keeps_moves_and_hp_ratio():
    m = mon("brookfin", 15)
    m.hp = m.max_hp // 2
    m.moves[0]["pp"] = 3
    leveling.grant_xp(m, leveling.xp_to_next(15) + 1)
    assert m.species_id == "riverfin"
    assert m.moves[0]["id"] == "splash_lash"
    assert m.moves[0]["pp"] == 3
    assert m.hp == m.max_hp // 2 or abs(m.hp - m.max_hp // 2) <= 1


def test_no_evolution_for_fully_evolved():
    m = mon("granitewyrm", 40)
    assert leveling.check_evolution(m) is None


def test_battle_shows_evolution_message():
    pygame.init()
    game = FakeGame()
    game.world.party = [mon("mossrat", 15)]
    m = game.world.party[0]
    m.xp = leveling.xp_to_next(15) - 1  # one win pushes past the evolution level
    battle = BattleScene(game, m, mon("mossrat", 2))
    battle.intro_timer = 0
    battle.enemy_mon.hp = 0
    battle._check_outcome()
    assert battle.outcome == "won"
    assert any("evolved" in msg.lower() for msg in battle.messages)


def test_roll_wild_scales_with_party():
    zone = {"encounters": {"mossrat": 1}, "encounter_levels": [2, 5]}
    party = [mon("fernpup", 20)]
    for _ in range(20):
        wild = roll_wild(zone, party=party)
        assert wild.level >= 2
        assert wild.level <= 20 + 5  # never more than best + 5 (spec 9.3)


def test_roll_wild_without_party_uses_zone_levels():
    zone = {"encounters": {"mossrat": 1}, "encounter_levels": [2, 5]}
    for _ in range(20):
        wild = roll_wild(zone)
        assert 2 <= wild.level <= 5


def test_legendaries_exist():
    species = load_species()
    legendaries = [sid for sid, s in species.items() if s["tier"] == 4]
    assert len(legendaries) >= 3


def test_damage_handles_dual_types():
    chart = __import__("src.monsters.monster", fromlist=["load_type_chart"]).load_type_chart()
    # water vs leaf/stone dual: water beats stone (2x), leaf resists? leaf doesn't resist water
    mult = battle_mod.type_multiplier("water", ["stone", "leaf"], chart)
    assert mult == 2.0
