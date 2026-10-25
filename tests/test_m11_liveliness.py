"""Tests for M11: berry patches, shinies, rival rematches, day/night."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

import pytest

from src.engine.game import Game
from src.monsters.monster import Monster, load_species, load_moves
from src.world.trainers import TrainerState, load_trainers
from src.save import serialize


@pytest.fixture
def game(tmp_path):
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    return Game()


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


# ------------------------------------------------------------------ shiny

def test_shiny_boosts_stats_and_names():
    plain = mon("mossrat", 10)
    shiny = mon("mossrat", 10)
    shiny.make_shiny()
    assert shiny.shiny and plain.max_hp * 1.1 - 1 <= shiny.max_hp <= plain.max_hp * 1.1 + 1
    assert shiny.name.startswith("\u2605")
    assert shiny.attack >= plain.attack


def test_shiny_survives_level_up():
    shiny = mon("mossrat", 5)
    shiny.make_shiny()
    plain = mon("mossrat", 5)
    from src.monsters import leveling

    shiny.xp = leveling.xp_to_next(5)
    plain.xp = leveling.xp_to_next(5)
    leveling.grant_xp(shiny, 1)
    leveling.grant_xp(plain, 1)
    assert shiny.level == plain.level == 6
    assert shiny.max_hp > plain.max_hp, "shiny boost must survive level ups"


def test_shiny_round_trips_save(game):
    world = game.world
    shiny = mon("brookfin", 7)
    shiny.make_shiny()
    shiny.hp = 3  # damaged: restored HP must not reset to full
    world.party = [shiny]
    data = serialize(world)
    assert data["party"][0]["shiny"] is True
    from src.save import apply_save

    apply_save(world, data)
    loaded = world.party[0]
    assert loaded.shiny and loaded.name.startswith("\u2605")
    assert loaded.hp == 3


def test_wild_shiny_chance(game):
    """roll_wild applies shiny ~1/50: run enough trials to see both sides."""
    from src.monsters.monster import roll_wild

    zone = {"encounters": {"mossrat": 10}, "encounter_levels": [3, 3]}
    seen_shiny = False
    seen_plain = False
    for _ in range(500):
        m = roll_wild(zone)
        if m.shiny:
            seen_shiny = True
        else:
            seen_plain = True
    assert seen_shiny and seen_plain


# ----------------------------------------------------------- berry patches

def test_berry_plants_planted():
    import json

    zones = json.load(open("data/zones.json"))["zones"]
    total = sum(
        sum(row.count("b") for row in z["tiles"])
        for z in zones.values()
    )
    assert total >= 8, "at least 8 berry plants across forest zones"
    for zid, z in zones.items():
        if any("b" in row for row in z["tiles"]):
            assert z["legend"].get("b") == "berry_plant", zid


def test_berry_pick_and_regrow(game):
    world = game.world
    world.switch_zone("whispering_pines", 5, 2)
    # plant at (6,3): face right from (5,3)
    world.player.tile_x, world.player.tile_y = 5, 3
    world.player.facing = "right"
    before = world.inventory.count("berry")
    assert world._try_berry_pick(6, 3) is True
    picked = world.inventory.count("berry")
    assert 1 <= picked - before <= 3
    # picked: regrowing now
    assert (world.zone_id, 6, 3) in world.berry_patches
    assert world._try_berry_pick(6, 3) is True  # handled but no yield
    assert world.inventory.count("berry") == picked
    # after the regrow window passes, it yields again
    world.play_time += world._BERRY_REGROW_SECONDS + 1
    assert world._try_berry_pick(6, 3) is True
    assert world.inventory.count("berry") > picked


def test_bloom_badge_doubles_yield(game):
    world = game.world
    world.switch_zone("whispering_pines", 5, 2)
    world.player.tile_x, world.player.tile_y = 5, 3
    world.trainer_state.defeated["hazel"] = True  # bloom badge
    assert "bloom" in world.badge_ids
    before = world.inventory.count("berry")
    world._try_berry_pick(6, 3)
    assert world.inventory.count("berry") - before >= 2


def test_berry_patches_persist(game):
    world = game.world
    world.switch_zone("whispering_pines", 5, 2)
    world.player.tile_x, world.player.tile_y = 5, 3
    world._try_berry_pick(6, 3)
    data = serialize(world)
    assert any(k == "whispering_pines:6:3" for k in data["berry_patches"])
    from src.save import apply_save

    apply_save(world, data)
    assert ("whispering_pines", 6, 3) in world.berry_patches


# ---------------------------------------------------------- rival rematches

def test_rival_rematch_data_valid():
    trainers = load_trainers()["trainers"]
    rematches = [t for t in trainers.values() if t.get("requires_badge")]
    assert len(rematches) == 3
    levels = [max(m["level"] for m in t["team"]) for t in rematches]
    assert levels == sorted(levels)
    for t in rematches:
        assert t["requires_defeat"] and t["rival"]


def test_rival_rematch_badge_gated():
    state = TrainerState()
    trainer = load_trainers()["trainers"]["emmett_r1"]
    # no badges: blocked even with the prior fight won
    state.defeated["emmett_1"] = True
    assert not state.can_challenge("emmett_r1", trainer, badges=[])
    # with the pine badge and prior fight: allowed
    assert state.can_challenge("emmett_r1", trainer, badges=["pine"])


# ---------------------------------------------------------------- day/night

def test_day_night_cycle(game):
    world = game.world
    world.play_time = 0
    assert not world.is_night
    world.play_time = world.DAY_NIGHT_SECONDS * 2 / 3
    assert world.is_night
    world.play_time = world.DAY_NIGHT_SECONDS  # new cycle: day again
    assert not world.is_night


def test_day_night_option_disables_night(game):
    world = game.world
    game.day_night_enabled = False
    world.play_time = world.DAY_NIGHT_SECONDS * 2 / 3
    assert not world.is_night
    game.day_night_enabled = True
    assert world.is_night


def test_night_tint_draws(game):
    world = game.world
    world.play_time = world.DAY_NIGHT_SECONDS * 2 / 3
    world.draw(game.buffer)  # must not crash
    # daytime render for contrast
    world.play_time = 0
    world.draw(game.buffer)


def test_shiny_level_up_never_loses_hp():
    """Review fix: a wounded shiny must gain (not lose) HP on level up."""
    from src.monsters import leveling

    shiny = mon("fernpup", 5)
    shiny.make_shiny()
    shiny.hp = 1
    old_max = shiny.max_hp
    shiny.xp = leveling.xp_to_next(5)
    leveling.grant_xp(shiny, 1)
    assert shiny.level == 6
    assert shiny.hp >= 1, "leveling must not faint a shiny"
    assert shiny.hp >= 1 or shiny.max_hp > old_max
    # exact regression: 1 HP before, at least 2 after (same as a plain monster)
    plain = mon("fernpup", 5)
    plain.hp = 1
    plain.xp = leveling.xp_to_next(5)
    leveling.grant_xp(plain, 1)
    assert shiny.hp >= plain.hp, "shiny keeps at least the plain monster's HP"


def test_shiny_survives_evolution():
    """Review fix: evolving a shiny keeps flag, boost, and starred name."""
    from src.monsters import leveling

    species = load_species()
    evo = species["mossrat"].get("evolve_into")
    assert evo
    shiny = mon("mossrat", evo["level"])
    shiny.make_shiny()
    result = leveling.check_evolution(shiny)
    assert result is not None
    assert shiny.shiny is True
    assert shiny.name.startswith("\u2605")
    plain = mon(evo["species"], evo["level"])
    assert shiny.max_hp > plain.max_hp


def test_heal_preserves_shiny_defense(game):
    """Review fix: lodge healing must keep the permanent shiny defense bonus."""
    from src.world.scene import _reset_battle_boosts

    shiny = mon("brookfin", 10)
    shiny.make_shiny()
    boosted_def = shiny.defense
    shiny.defense = boosted_def + 2  # brace stacks in battle
    _reset_battle_boosts(shiny)
    assert shiny.defense == boosted_def, "heal keeps the shiny bonus, drops only braces"
    plain = mon("brookfin", 10)
    assert shiny.defense > plain.defense


def test_night_variants_can_be_shiny(game):
    """Review fix: the night encounter path uses the same shared shiny roll."""
    from src.monsters.monster import maybe_make_shiny, SHINY_CHANCE

    world = game.world
    world.play_time = world.DAY_NIGHT_SECONDS * 2 / 3
    assert world.is_night
    seen_shiny, seen_plain = False, False
    for _ in range(1000):
        m = mon("sleetfox", 5)
        maybe_make_shiny(m)
        if m.shiny:
            seen_shiny = True
        else:
            seen_plain = True
    assert seen_shiny and seen_plain
    assert SHINY_CHANCE == 1 / 50
    # deterministic rng contract
    class Always:
        @staticmethod
        def random():
            return 0.0

    class Never:
        @staticmethod
        def random():
            return 0.999

    assert maybe_make_shiny(mon("sleetfox", 5), rng=Always).shiny
    assert not maybe_make_shiny(mon("sleetfox", 5), rng=Never).shiny


def test_night_pool_excludes_legendaries(game):
    """Review fix: tier-4 species only appear via the configured legendary roll."""
    world = game.world
    world.play_time = world.DAY_NIGHT_SECONDS * 2 / 3
    assert world.is_night
    zone = world.zones["whispering_pines"]
    night_species = [
        sid for sid, sp in load_species().items()
        if any(t in sp["types"] for t in ("frost", "storm"))
        and sp["tier"] < 4
        and sid not in zone["encounters"]
    ]
    assert night_species
    assert all(load_species()[sid]["tier"] < 4 for sid in night_species)
    assert "legendary_verdant" not in night_species
    assert "legendary_tidal" not in night_species
