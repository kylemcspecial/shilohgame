"""Tests for M10 zone puzzles: boulder, stones, riddles, lanterns."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

import pytest

from src.engine.game import Game
from src.world.scene import WorldScene, load_zones
from src.world import puzzles as pz


@pytest.fixture
def game(tmp_path):
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    return Game()


def zone_with_puzzle(game, zid):
    world = game.world
    world.trainer_state.defeated[
        {  # beat the zone leader so the leader gate is open
            "pineroot_crossing": "boulder",
            "mossy_hollow": "ivy",
            "thornwood_ridge": "rex",
            "mossy_hollow_gate": "bram",
        }[zid]
    ] = True
    start = (5, 11) if zid in ("pineroot_crossing", "mossy_hollow_gate") else (4, 11)
    world.switch_zone(zid, *start)
    return world


# ------------------------------------------------------------- definitions

def test_puzzle_defs_valid():
    zones = load_zones()["zones"]
    puzzle_zones = [z for z in zones.values() if z.get("puzzle")]
    assert len(puzzle_zones) == 4
    for z in puzzle_zones:
        p = z["puzzle"]
        assert p["type"] in ("boulder", "stones", "riddles", "lanterns")
        assert p["id"] and p["hint"]
        assert z["tiles"][p["gate"]["y"]][p["gate"]["x"]] == "D"


def test_puzzle_tiles_exist():
    zones = load_zones()["zones"]
    p = zones["pineroot_crossing"]["puzzle"]
    for x, y in p["switches"]:
        assert zones["pineroot_crossing"]["tiles"][y][x] == "o"
    p = zones["mossy_hollow"]["puzzle"]
    for x, y in p["sequence"]:
        assert zones["mossy_hollow"]["tiles"][y][x] == "~"


# ------------------------------------------------------------------ boulder

def test_pushed_boulder_leaves_no_ghost_tile(game):
    """After init, static B tiles must be cleared: runtime boulders own collision."""
    world = zone_with_puzzle(game, "pineroot_crossing")
    p = world._puzzle_def()
    for bx, by in p["boulders"]:
        assert world.tile_map.tile_at(bx, by) == ".", (bx, by)
        assert not world.tile_map.is_solid(bx, by)
    # the vacated square stays walkable after a push
    world.player.tile_x, world.player.tile_y = 6, 9
    assert world._try_boulder_push({"right"}) == "pushed"
    assert not world.tile_map.is_solid(7, 9), "vacated boulder tile must be walkable"


def test_stone_hint_shows_the_dance(game):
    """Interacting with the hint stone must present the sequence, not just text."""
    world = zone_with_puzzle(game, "mossy_hollow")
    p = world._puzzle_def()
    assert world.dance_timer == 0.0
    handled = world._try_puzzle_interact(4, 10)  # the ? hint stone
    assert handled is True
    assert world.dance_timer > 0
    # and while it runs, drawing shows the numbered stones (no crash, HUD)
    world.draw(game.buffer)
    assert world.dance_timer > 0


def test_boulder_push_moves_and_stops(game):
    world = zone_with_puzzle(game, "pineroot_crossing")
    p = world._puzzle_def()
    assert not world.puzzles.solved("boulder")
    assert (7, 9) in world.boulders
    # stand left of the boulder at (7,9), face right, push
    world.player.tile_x, world.player.tile_y = 6, 9
    world.player.px, world.player.py = 6 * 16, 9 * 16
    world.player.moving = False
    result = world._try_boulder_push({"right"})
    assert result == "pushed"
    assert (8, 9) in world.boulders
    # pushing into a solid tile is blocked
    world.boulders[0] = (18, 1)  # against the right tree border
    world.player.tile_x, world.player.tile_y = 17, 1
    assert world._try_boulder_push({"right"}) == "blocked"


def test_boulder_puzzle_solves_and_opens_gate(game):
    world = zone_with_puzzle(game, "pineroot_crossing")
    p = world._puzzle_def()
    warp = world.tile_map.warp_at(9, 12)
    # leader beaten but puzzle unsolved: sealed
    assert world._gate_block(warp) is not None
    world.boulders = [tuple(s) for s in p["switches"]]
    world.player.tile_x, world.player.tile_y = 9, 12
    world._on_step()
    assert world.puzzles.solved("boulder")
    assert world._gate_block(warp) is None


def test_gate_blocked_by_puzzle_even_with_badge(game):
    world = zone_with_puzzle(game, "pineroot_crossing")
    warp = world.tile_map.warp_at(9, 12)
    blocked = world._gate_block(warp)
    assert blocked is not None and "sealed" in blocked


# ------------------------------------------------------------------- stones

def test_stones_wrong_step_resets(game):
    world = zone_with_puzzle(game, "mossy_hollow")
    p = world._puzzle_def()
    seq = [tuple(s) for s in p["sequence"]]
    ok, entered = pz.stones_step(seq, [], seq[0])
    assert ok and entered == [seq[0]]
    ok, entered = pz.stones_step(seq, entered, seq[2])  # wrong order
    assert not ok and entered == []


def test_stones_full_sequence_solves(game):
    world = zone_with_puzzle(game, "mossy_hollow")
    p = world._puzzle_def()
    seq = [tuple(s) for s in p["sequence"]]
    world.player.tile_x, world.player.tile_y = seq[0]
    world._puzzle_step()
    entered = world.stones_entered
    for tile in seq[1:]:
        world.player.tile_x, world.player.tile_y = tile
        world._puzzle_step()
        entered = world.stones_entered
    assert world.puzzles.solved("stones")
    assert world._gate_block(world.tile_map.warp_at(10, 11)) is None


# ------------------------------------------------------------------ riddles

def test_riddle_menu_answers(game):
    world = zone_with_puzzle(game, "thornwood_ridge")
    p = world._puzzle_def()
    r = p["riddles"][0]
    world.riddle_menu = r
    world.answer_index = r["correct"]
    world.game.input.pressed = {"confirm"}
    world._update_riddle_menu()
    state = world.puzzles.state["riddles"]
    assert state["answers"]["r1"] is True
    # wrong answers recorded false; not solved until all three
    r2 = p["riddles"][1]
    world.riddle_menu = r2
    world.answer_index = (r2["correct"] + 1) % 3
    world.game.input.pressed = {"confirm"}
    world._update_riddle_menu()
    assert not world.puzzles.solved("riddles")


def test_all_riddles_correct_solves(game):
    world = zone_with_puzzle(game, "thornwood_ridge")
    p = world._puzzle_def()
    for r in p["riddles"]:
        world.riddle_menu = r
        world.answer_index = r["correct"]
        world.game.input.pressed = {"confirm"}
        world._update_riddle_menu()
    assert world.puzzles.solved("riddles")
    assert world._gate_block(world.tile_map.warp_at(10, 11)) is None


# ----------------------------------------------------------------- lanterns

def test_lantern_toggle_flips_neighbors(game):
    on = [True, False, False, True]
    layout = [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]
    on = pz.lantern_toggle(on, 0, layout)
    assert on == [False, True, True, True]


def test_lanterns_solvable_from_start_state(game):
    """The 2x2 lights-out start [T,F,F,T] must reach all-on."""
    import itertools

    start = [True, False, False, True]
    layout = [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]
    found = None
    for n in range(1, 5):
        for presses in itertools.product(range(4), repeat=n):
            on = list(start)
            for idx in presses:
                on = pz.lantern_toggle(on, idx, layout)
            if all(on):
                found = presses
                break
        if found:
            break
    assert found, "lantern puzzle must be solvable"
    # and the zone solves via interactions
    world = zone_with_puzzle(game, "mossy_hollow_gate")
    p = world._puzzle_def()
    assert world.lanterns_on == start
    for idx in found:
        world.riddle_menu = None
        lx, ly = p["lanterns"][idx]
        world._try_puzzle_interact(lx, ly)
    assert world.puzzles.solved("lanterns")


def test_lantern_state_persists(game, tmp_path):
    world = zone_with_puzzle(game, "mossy_hollow_gate")
    world.lanterns_on = pz.lantern_toggle(world.lanterns_on, 1,
                                          world._puzzle_def()["layout"])
    world.puzzles.set("lanterns", "state", list(world.lanterns_on))
    from src.save import serialize, load_game, save_game, apply_save

    data = serialize(world)
    assert data["puzzle_state"]["lanterns"]["state"] == world.lanterns_on
    save_game(world, 0)
    loaded = load_game(0)
    assert loaded["puzzle_state"]["lanterns"]["state"] == world.lanterns_on
    apply_save(world, loaded)
    assert world.lanterns_on == list(loaded["puzzle_state"]["lanterns"]["state"])


def test_solved_puzzle_persists_and_gate_stays_open(game):
    world = zone_with_puzzle(game, "pineroot_crossing")
    world.puzzles.mark_solved("boulder")
    from src.save import serialize

    data = serialize(world)
    assert data["puzzle_state"]["boulder"]["solved"] is True
    # re-init keeps it solved (save/load round trip simulation)
    world._init_puzzle_state()
    assert world.puzzles.solved("boulder")
    assert world.boulders == [tuple(s) for s in world._puzzle_def()["switches"]]
