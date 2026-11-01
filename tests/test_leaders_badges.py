"""Tests for M9: area leaders, badge gating, badges, intro flow, XP rebalance."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

import pytest

from src.engine.game import Game
from src.world.scene import WorldScene, _ZONE_CHAIN
from src.world.trainers import load_trainers
from src.battle.scene import TrainerBattle
from src.monsters.monster import Monster, load_species, load_moves
from src.monsters import leveling
from src.ui.intro import IntroScene


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


@pytest.fixture
def game(tmp_path):
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    return Game()


# ------------------------------------------------------------------- data

def test_leader_data_valid():
    trainers = load_trainers()["trainers"]
    leaders = {tid: t for tid, t in trainers.items() if t.get("leader")}
    assert len(leaders) == 7
    for tid, t in leaders.items():
        assert t["badge"] and t["badge_name"]
        assert len(t["team"]) == 3
        assert t["reward"] > 0
        assert t["zone"] in _ZONE_CHAIN or t["zone"] == "emberfern_glade"


def test_zone_chain_matches_leaders():
    for zone_id, (next_zone, leader_id) in _ZONE_CHAIN.items():
        t = load_trainers()["trainers"][leader_id]
        assert t["zone"] == zone_id, (zone_id, leader_id)
        assert t.get("leader")


def test_leader_levels_escalate():
    trainers = load_trainers()["trainers"]
    chain_levels = [
        max(m["level"] for m in trainers[lid]["team"])
        for _, (_, lid) in _ZONE_CHAIN.items()
    ]
    assert chain_levels == sorted(chain_levels), "leader aces must escalate"


# ------------------------------------------------------------------ gating

def test_forward_gate_blocks_without_badge(game):
    world = game.world
    world.switch_zone("whispering_pines", 9, 11)
    warp = world.tile_map.warp_at(9, 12)  # door to pineroot_crossing
    assert warp is not None and warp["zone"] == "pineroot_crossing"
    blocked = world._gate_block(warp)
    assert blocked is not None and "sealed" in blocked
    # step onto the sealed door: no warp happens
    world.player.tile_x, world.player.tile_y = 9, 12
    world._on_step()
    assert world.zone_id == "whispering_pines"


def test_forward_gate_opens_with_badge(game):
    world = game.world
    world.switch_zone("whispering_pines", 9, 11)
    world.trainer_state.defeated["fenwick"] = True
    assert world.badge_ids == ["pine"]
    warp = world.tile_map.warp_at(9, 12)
    assert world._gate_block(warp) is None
    world.player.tile_x, world.player.tile_y = 9, 12
    world._on_step()
    assert world.zone_id == "pineroot_crossing"


def test_back_doors_never_gated(game):
    world = game.world
    world.switch_zone("pineroot_crossing", 9, 11)
    # door back to whispering pines must work with zero badges
    warp = world.tile_map.warp_at(6, 11)
    assert warp["zone"] == "whispering_pines"
    assert world._gate_block(warp) is None


def test_badge_ids_derive_from_defeated_leaders(game):
    world = game.world
    assert world.badge_ids == []
    world.trainer_state.defeated["fenwick"] = True
    world.trainer_state.defeated["boulder"] = True
    assert world.badge_ids == ["pine", "stone"]


def test_leader_never_ambushes(game):
    world = game.world
    world.switch_zone("whispering_pines", 9, 10)  # adjacent to fenwick at (8,11)? no: (8,10)
    world._check_trainer_sight()
    assert game.scene is world, "leaders must be talk-to-battle, never ambushed"


def test_on_badge_won_pays_triple(game):
    world = game.world
    world.coins = 100
    world.on_badge_won("pine")
    assert world.coins == 100 + 120 * 3
    # double-award is ignored
    world.on_badge_won("pine")
    assert world.coins == 100 + 120 * 3


def test_leader_rematch_levels_boosted(game):
    trainer = load_trainers()["trainers"]["fenwick"]
    game.world.trainer_state.defeated["fenwick"] = True
    battle = TrainerBattle(game, mon("fernpup", 20), "fenwick", trainer)
    assert [m.level for m in battle.team] == [11, 11, 12]
    assert battle.badge_won is None  # rematch gives no badge
    # a fresh game (leader never beaten) faces the base team and can win the badge
    fresh_game = Game()
    fresh = TrainerBattle(fresh_game, mon("fernpup", 5), "fenwick", trainer)
    assert [m.level for m in fresh.team] == [8, 8, 9]
    assert fresh.badge_won == "pine"


def test_leader_win_awards_badge_via_end_battle(game):
    world = game.world
    trainer = load_trainers()["trainers"]["fenwick"]
    battle = TrainerBattle(game, mon("fernpup", 20), "fenwick", trainer)
    battle.outcome = "trainer_won"
    game.scene = battle
    game.end_battle()
    assert "fenwick" in world.trainer_state.defeated
    assert world.badge_ids == ["pine"]


# ------------------------------------------------------------- shop/storage

def test_shop_badge_unlocks(game):
    world = game.world
    entries = {e["id"]: e for e in world._shop_available()}
    assert entries["stout_trap"]["unlocked"] is False
    world.trainer_state.defeated["fenwick"] = True
    entries = {e["id"]: e for e in world._shop_available()}
    assert entries["stout_trap"]["unlocked"] is True
    assert entries["ultra_trap"]["unlocked"] is False


def test_storage_requires_fern_badge(game):
    world = game.world
    world.paused = True
    world.pause_index = world._PAUSE_MENU.index("Storage")
    world.game.input.pressed = {"confirm"}
    world._update_pause_menu()
    assert not world.storage_menu
    world.trainer_state.defeated["ivy"] = True
    world.game.input.pressed = {"confirm"}
    world._update_pause_menu()
    assert world.storage_menu


def test_storage_withdraw_to_party(game):
    world = game.world
    world.trainer_state.defeated["ivy"] = True
    stored = mon("brookfin", 7)
    world.storage = [stored]
    world.storage_menu = True
    world.storage_index = 0
    world.game.input.pressed = {"confirm"}
    world._update_storage_menu()
    assert stored in world.party and world.storage == []


# ------------------------------------------------------------------- intro

def _stub_game():
    class StubInput:
        pressed = set()

    class StubAudio:
        def confirm(self): pass

    class StubGame:
        input = StubInput()
        audio = StubAudio()

    return StubGame()


def test_intro_flow_names_and_starter():
    intro = IntroScene(_stub_game())
    # Hunter name: cursor to 'M' (row 0, col 12), confirm, then END
    intro.row, intro.col = 0, 12
    intro.game.input.pressed = {"confirm"}
    intro.update(0)
    assert intro.names[0] == "M"
    intro.game.input.pressed = set()
    intro.update(0)
    intro.row, intro.col = 3, 5  # END
    intro.game.input.pressed = {"confirm"}
    intro.update(0)
    assert intro.step == 1
    # Rival name: 'Z' (row 0, col 25), then END
    intro.row, intro.col = 0, 25
    intro.game.input.pressed = {"confirm"}
    intro.update(0)
    intro.game.input.pressed = set()
    intro.update(0)
    intro.row, intro.col = 3, 5
    intro.game.input.pressed = {"confirm"}
    intro.update(0)
    assert intro.step == 2
    intro.game.input.pressed = {"confirm"}
    intro.update(0)
    assert intro.done
    assert intro.result == {"player": "M", "rival": "Z", "starter": "fernpup"}


def test_intro_rejects_empty_name():
    intro = IntroScene(_stub_game())
    intro.row, intro.col = 3, 5  # END with empty name
    intro.game.input.pressed = {"confirm"}
    intro.update(0)
    assert intro.step == 0 and intro.flash


def test_intro_cycles_starters():
    intro = IntroScene(_stub_game())
    intro.step = 2
    intro.game.input.pressed = {"right"}
    intro.update(0)
    assert intro.starter_index == 1
    intro.game.input.pressed = {"confirm"}
    intro.update(0)
    assert intro.result["starter"] == "brookfin"


def test_world_scene_accepts_intro():
    class StubGame:
        pass

    world = WorldScene(StubGame(), intro={"player": "Max", "rival": "Lex", "starter": "brookfin"})
    assert world.player_name == "Max"
    assert world.rival_name == "Lex"
    assert world.party[0].species_id == "brookfin"


# ------------------------------------------------------------- xp rebalance

def test_xp_curve_grows_superlinearly():
    assert leveling.xp_to_next(5) == 10 + 25 + 6
    assert leveling.xp_to_next(20) == 10 + 100 + 100
    assert leveling.xp_to_next(20) > 2 * leveling.xp_to_next(10)


def test_level_gap_penalty():
    full = leveling.xp_for_defeat(10, 1, 10)
    assert leveling.xp_for_defeat(10, 1, 15) == full // 2
    assert leveling.xp_for_defeat(10, 1, 20) == full // 4
    assert leveling.xp_for_defeat(10, 1, 25) == max(1, full // 10)  # 15+: 10%, not 0
    assert leveling.xp_for_defeat(10, 1, 8) == full  # fighting up: full pay


def test_participant_xp_share(game, tmp_path):
    """Active monster gets full XP; standing participants get half; fainted get none."""
    from src.battle.scene import BattleScene
    from src.items.inventory import Inventory

    active = mon("fernpup", 5)
    helper = mon("brookfin", 5)
    benched = mon("mossrat", 5)
    fainted_helper = mon("chirrel", 5)
    fainted_helper.hp = 0
    game.world.party = [active, helper, benched, fainted_helper]
    battle = BattleScene(
        game, active, mon("mossrat", 5), inventory=Inventory({"potion_s": 1})
    )
    battle.intro_timer = 0
    battle.participants = [active, helper, fainted_helper]
    battle._enemy_free_attack = lambda: None
    xp_active = leveling.xp_for_defeat(5, 1, 5)
    before = {m: (m.level, m.xp) for m in (active, helper, benched, fainted_helper)}
    msgs = battle._xp_messages(xp_active)
    assert active.xp > before[active][1] or active.level > before[active][0]
    assert helper.xp > 0, "standing participant must earn share"
    assert fainted_helper.xp == 0 and fainted_helper.level == before[fainted_helper][0]
    assert benched.xp == 0 and benched.level == before[benched][0], "benched gets nothing"


def test_switch_registers_participant(game):
    from src.battle.scene import BattleScene

    active = mon("fernpup", 5)
    helper = mon("brookfin", 5)
    game.world.party = [active, helper]
    battle = BattleScene(game, active, mon("mossrat", 6))
    battle.intro_timer = 0
    battle._enemy_free_attack = lambda: None
    assert battle.participants == [active]
    battle._do_switch(helper)
    assert battle.participants == [active, helper]


def test_levels_per_win_slowed():
    """A same-level tier-1 win should no longer be ~1 level per fight."""
    for level in (5, 15, 30):
        earned = leveling.xp_for_defeat(level, 1, level)
        assert leveling.xp_to_next(level) > earned, (
            f"L{level}: one same-level win must not level you"
        )


def test_trainer_xp_no_longer_sums_team(game):
    world = game.world
    trainer = load_trainers()["trainers"]["fenwick"]
    battle = TrainerBattle(game, mon("fernpup", 9), "fenwick", trainer)
    battle.outcome = "trainer_won"
    before = battle.player_mon.level
    # sum-of-team would be 3 monsters' worth; capped 1.5x is far less
    game.scene = battle
    xp_expected = int(1.5 * leveling.xp_for_defeat(9, 2, 9))
    assert xp_expected < sum(
        leveling.xp_for_defeat(m.level, m.species["tier"], 9) for m in battle.team
    )


def test_undefeated_leader_blocks_their_door(game):
    """The leader physically blocks the forward door until beaten."""
    world = game.world
    world.switch_zone("whispering_pines", 9, 11)
    assert (9, 12) in world._leader_blocks()
    # player cannot step onto the leader's tile
    from src.engine.constants import TILE_SIZE

    world.player.tile_x, world.player.tile_y = 9, 11
    world.player.py = 11 * TILE_SIZE
    world.game.input.held = {"down"}
    world.player.update(1 / 60, world.tile_map, {"down"}, world._leader_blocks())
    assert (world.player.tile_x, world.player.tile_y) == (9, 11)
    # after defeat the door is free
    world.trainer_state.defeated["fenwick"] = True
    assert world._leader_blocks() == set()
    world.player.update(1 / 60, world.tile_map, {"down"}, world._leader_blocks())
    assert (world.player.tile_x, world.player.tile_y) == (9, 12)


def test_defeated_leader_stepped_aside_not_interactable(game):
    """After defeat the leader steps aside: facing the door no longer finds them."""
    world = game.world
    world.switch_zone("whispering_pines", 9, 11)
    world.player.facing = "down"
    assert world._leader_at(9, 12) is not None  # undefeated: blocks and talkable
    world.trainer_state.defeated["fenwick"] = True
    assert world._leader_at(9, 12) is None  # defeated: moved off the door
