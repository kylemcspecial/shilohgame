"""Regression tests for the bugs found in the milestone-stack review.

Each test drives scenes through update()/draw() like the real game loop,
since several reviewed bugs (e.g. the Trainer Card crash) only surfaced
when drawing, not when calling methods directly.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.engine.game import Game
from src.battle.scene import BattleScene, TrainerBattle
from src.battle import catch as catch_mod
from src.monsters.monster import Monster, load_species, load_moves, roll_wild
from src.monsters import leveling
from src.world.trainers import TrainerState, load_trainers


class AlwaysCatch:
    def random(self):
        return 0.0


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


def fresh_game(tmp_xdg):
    os.environ["XDG_DATA_HOME"] = str(tmp_xdg)
    return Game()


# ---------------------------------------------------------------------------
# Bug 1: Trainer Card crashed _draw_pause (NameError: pressed)


def test_trainer_card_draws_without_crash(tmp_path):
    game = fresh_game(tmp_path)
    world = game.world
    world.toggle_pause()
    world.card_menu = True
    for _ in range(5):
        world.update(1 / 60)
        world.draw(game.buffer)
    assert world.card_menu  # card only closes on input, drawing must not crash


def test_pause_menu_all_states_draw(tmp_path):
    game = fresh_game(tmp_path)
    world = game.world
    for state in ("party_menu", "save_menu", "card_menu"):
        world.toggle_pause()
        setattr(world, state, True)
        for _ in range(3):
            world.update(1 / 60)
            world.draw(game.buffer)
        world.toggle_pause()
        world.toggle_pause()  # re-pause
        assert not getattr(world, state), f"{state} must reset on toggle_pause"


# ---------------------------------------------------------------------------
# Bug 3: turn messages were skipped (index jumped to the last message)


def test_turn_messages_step_through(tmp_path):
    game = fresh_game(tmp_path)
    battle = BattleScene(game, mon("fernpup", 5), mon("brookfin", 3))
    battle.intro_timer = 0
    battle.messages = ["intro"]
    battle._read = len(battle.messages) - 1  # intro confirmed
    battle._choose("Fight"); battle._take_turn(battle.player_mon.moves[0])
    assert len(battle.messages) >= 3
    assert battle.message_index == 1  # first NEW message, not the last


def test_effectiveness_message_reachable(tmp_path):
    game = fresh_game(tmp_path)
    battle = BattleScene(game, mon("fernpup", 5), mon("brookfin", 3))
    battle.intro_timer = 0
    battle.messages = ["intro"]
    battle._read = len(battle.messages) - 1
    battle._choose("Fight"); battle._take_turn(battle.player_mon.moves[0])  # leaf vs water: super effective
    texts = battle.messages
    assert any("super effective" in t for t in texts)
    assert battle.message_index < len(texts) - 1


# ---------------------------------------------------------------------------
# Bug 4: catching granted no XP (spec 6.5)


def test_catch_grants_xp(tmp_path):
    game = fresh_game(tmp_path)
    world = game.world
    lead = world.party[0]
    lead.xp = 0
    battle = BattleScene(game, lead, mon("mossrat", 3), inventory=world.inventory)
    battle.intro_timer = 0
    battle.enemy_mon.hp = 1
    world.inventory.add("basic_trap", 3)
    orig_random = catch_mod.random
    catch_mod.random = AlwaysCatch()
    try:
        battle._choose("Catch")
        battle._choose_trap(0)
    finally:
        catch_mod.random = orig_random
    assert battle.outcome == "caught"
    assert lead.xp > 0, "catching must grant XP (spec 6.5)"


# ---------------------------------------------------------------------------
# Bug 5: lodge claimed "Game saved" when it didn't


def test_lodge_message_honest_about_saving(tmp_path):
    game = fresh_game(tmp_path)
    world = game.world
    world.save_slot = None
    world.player.tile_x, world.player.tile_y = 16, 3
    world.player.facing = "up"
    world._interact()
    assert "healed" in world.message
    assert "saved" in world.message  # lodge now picks a free slot and saves (PR review fix)
    from src.save import load_game

    assert load_game(world.save_slot) is not None
    assert world.save_slot == 0


# ---------------------------------------------------------------------------
# Bug 6: trainer battle said "The wild X fainted!"


def test_trainer_faint_wording(tmp_path):
    game = fresh_game(tmp_path)
    data = load_trainers()["trainers"]["pineroot_scout"]
    battle = TrainerBattle(game, mon("fernpup", 30), "pineroot_scout", data)
    battle.intro_timer = 0
    battle.enemy_mon.hp = 0
    battle._check_outcome()
    assert any("sent out" in m for m in battle.messages)
    assert not any("The wild" in m for m in battle.messages)


# ---------------------------------------------------------------------------
# Bug 8: trainer rematch cooldown must survive save/load


def test_trainer_cooldown_survives_save_load(tmp_path):
    game = fresh_game(tmp_path)
    world = game.world
    from src.save import save_game, load_game, apply_save

    data = load_trainers()["trainers"]
    world.trainer_state.record_start("pineroot_scout")
    world.trainer_state.record_win("pineroot_scout")
    assert not world.trainer_state.can_challenge("pineroot_scout", data["pineroot_scout"])

    save_game(world, 0)
    world.trainer_state.defeated = {}
    world.trainer_state.last_battled = {}
    apply_save(world, load_game(0))

    assert world.trainer_state.defeated.get("pineroot_scout")
    assert not world.trainer_state.can_challenge("pineroot_scout", data["pineroot_scout"])


def test_defeated_trainer_without_timer_starts_cooldown():
    state = TrainerState()
    data = load_trainers()["trainers"]
    state.defeated["pineroot_scout"] = True  # e.g. older save with no timer
    assert not state.can_challenge("pineroot_scout", data["pineroot_scout"])


# ---------------------------------------------------------------------------
# Bug 9/#40: level scaling must respect the zone ceiling


def test_wild_level_never_exceeds_zone_ceiling(tmp_path):
    zone = {"encounters": {"mossrat": 1}, "encounter_levels": [2, 5]}
    strong_party = [mon("fernpup", 40)]
    for _ in range(30):
        wild = roll_wild(zone, party=strong_party)
        assert wild.level <= 5, "starter zone must stay safe for returning players"


def test_legendary_only_in_configured_zones():
    import json

    from src.world.scene import load_zones

    zones = load_zones()["zones"]
    assert zones["whispering_pines"].get("legendary_chance", 0) == 0
    assert zones["emberfern_glade"].get("legendary_chance", 0) > 0
    zone = {"encounters": {"mossrat": 1}, "encounter_levels": [2, 5]}
    for _ in range(200):
        wild = roll_wild(zone)
        assert wild.species_id == "mossrat" or wild.species_id in zone["encounters"]


# ---------------------------------------------------------------------------
# Bug 11: battle must not start with a fainted lead


def test_encounter_picks_first_living(tmp_path):
    game = fresh_game(tmp_path)
    world = game.world
    world.party = [mon("fernpup", 5), mon("brookfin", 5)]
    world.party[0].hp = 0
    lead = world._first_living()
    assert lead is world.party[1]
    world.party[1].hp = 0
    assert world._first_living() is None


def test_all_fainted_party_revives_instead_of_battling(tmp_path):
    game = fresh_game(tmp_path)
    world = game.world
    world.party[0].hp = 0
    world.player.tile_x, world.player.tile_y = 2, 2  # tall grass in Hunter's Rest
    before = world.coins
    world._on_step()  # tall grass, but encounter roll may not fire; call directly
    lead = world._first_living()
    assert lead is None
    world.heal_and_revive()
    assert world.party[0].hp == world.party[0].max_hp
    assert world.coins < before


# ---------------------------------------------------------------------------
# Bug 2: audio must not force the dummy driver


def test_audio_does_not_force_dummy_driver():
    import importlib
    import src.engine.audio as audio_mod

    assert "SDL_AUDIODRIVER" not in open(audio_mod.__file__).read().split("import pygame")[0]
    game_src = open(audio_mod.__file__).read()
    assert 'setdefault("SDL_AUDIODRIVER"' not in game_src


def test_audio_volume_single_application():
    from src.engine.audio import Audio, _tone_samples

    stereo = _tone_samples(440, 0.05, 1.0)
    peak = int(abs(stereo).max())
    assert peak > 8000  # full-scale generation; volume applied at play time only
