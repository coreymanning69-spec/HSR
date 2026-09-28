"""fast_deepcopy must be observably identical to copy.deepcopy for run state."""
import copy
import random
from collections import OrderedDict

from hollowstar.actors import Actor
from hollowstar.fastcopy import fast_deepcopy
from hollowstar.rng import clone_random


def test_matches_deepcopy_on_nested_plain_state():
    state = {"a": [1, 2, {"b": (3, [4])}], "s": {5, 6}, "f": frozenset({7}), "n": None}
    clone = fast_deepcopy(state)
    assert clone == copy.deepcopy(state)
    assert clone["a"] is not state["a"]
    assert clone["a"][2]["b"][1] is not state["a"][2]["b"][1]
    clone["a"][2]["b"][1].append(9)
    assert state["a"][2]["b"][1] == [4]


def test_preserves_aliasing_and_self_reference():
    shared = [1]
    state = {"x": shared, "y": shared}
    state["me"] = state
    clone = fast_deepcopy(state)
    assert clone["x"] is clone["y"]
    assert clone["me"] is clone


def test_memo_seeded_payloads_are_shared_not_copied():
    config = {"big": list(range(10))}
    state = {"config": config, "live": [1]}
    clone = fast_deepcopy(state, {id(config): config})
    assert clone["config"] is config
    assert clone["live"] is not state["live"]


def test_subclasses_and_objects_take_the_deepcopy_path():
    ordered = OrderedDict(a=[1])
    actor = Actor(name="Doran")
    actor.resources["ki"] = 3
    clone = fast_deepcopy({"o": ordered, "actors": [actor, actor]})
    assert type(clone["o"]) is OrderedDict and clone["o"]["a"] is not ordered["a"]
    first, second = clone["actors"]
    assert first is second and first is not actor
    first.resources["ki"] = 0
    assert actor.resources["ki"] == 3


def test_actor_fast_clone_is_independent():
    actor = Actor(name="Wren")
    actor.statuses["prone"] = 1
    twin = actor.fast_clone()
    twin.statuses.clear()
    twin.hp -= 5
    assert actor.statuses == {"prone": 1} and actor.hp == 10


def test_clone_random_continues_the_same_stream_independently():
    source = random.Random("seed")
    source.random()
    twin = clone_random(source)
    assert [twin.random() for _ in range(5)] == [source.random() for _ in range(5)]
    twin.random()
    assert twin.getstate() != source.getstate()
