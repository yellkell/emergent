import numpy as np
import pytest
import torch

from emergent import make, list_worlds
from emergent.worlds import WORLDS

SMALL = {
    "gray-scott": dict(size=24, substeps=2),
    "lenia": dict(size=24, R=5),
    "particle-life": dict(n=60, size=48),
}


def test_registry_lists_all_worlds():
    assert set(list_worlds()) == {"gray-scott", "lenia", "particle-life", "neural-ca"}


@pytest.mark.parametrize("world", list(SMALL))
def test_world_runs_and_renders(world):
    uni = make(world, seed=0, **SMALL[world])
    img = uni.rule.render(uni.state)
    assert img.dtype == np.uint8 and img.ndim == 3 and img.shape[2] == 3
    uni.step(3)
    assert uni.rule.render(uni.state).shape == img.shape


@pytest.mark.parametrize("world", list(SMALL))
def test_presets_all_build(world):
    cls = WORLDS[world]
    for preset in cls.presets:
        rule = cls.build(preset, device=torch.device("cpu"))
        assert rule.name == world


def test_make_rejects_unknown_world():
    with pytest.raises(KeyError):
        make("hyperlife")


def test_gray_scott_stays_bounded():
    uni = make("gray-scott", size=24, substeps=2, seed=0)
    uni.step(25)
    assert uni.state.min() >= 0.0 and uni.state.max() <= 1.0 + 1e-5


def test_lenia_stays_in_unit_interval():
    uni = make("lenia", size=24, R=5, seed=0)
    uni.step(25)
    assert uni.state.min() >= -1e-6 and uni.state.max() <= 1.0 + 1e-6


def test_particle_positions_wrap_to_torus():
    uni = make("particle-life", n=80, size=48, seed=0)
    uni.step(15)
    pos = uni.state["pos"]
    assert float(pos.min()) >= 0.0 and float(pos.max()) < 1.0 + 1e-6
    # the world conserves particle count
    assert uni.state["types"].numel() == 80
