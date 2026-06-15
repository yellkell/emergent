import pytest
import torch

from emergent.core import Rule, Universe, describe_device, get_device
from emergent.worlds import GrayScott


def test_get_device_cpu():
    dev = get_device("cpu")
    assert dev.type == "cpu"
    assert "cpu" in describe_device(dev)


def test_get_device_auto_runs():
    # Whatever the backend, this must resolve to a real device.
    assert get_device("auto").type in {"cpu", "cuda", "mps"}


def test_get_device_rejects_garbage():
    with pytest.raises(ValueError):
        get_device("quantum")


def test_universe_advances_time():
    rule = GrayScott.build("coral", device=get_device("cpu"), size=16)
    uni = Universe(rule, seed=0)
    assert uni.t == 0
    uni.step(3)
    assert uni.t == 3
    info = uni.info()
    assert info["t"] == 3 and "V" in info


def test_universe_frames_count():
    rule = GrayScott.build("coral", device=get_device("cpu"), size=16, substeps=1)
    uni = Universe(rule, seed=0)
    frames = uni.record(steps=10, every=2)
    # one frame every 2 steps over 10 steps, plus a final frame
    assert len(frames) == 6
    assert frames[0].shape == frames[-1].shape


def test_rule_base_is_abstract():
    r = Rule()
    with pytest.raises(NotImplementedError):
        r.step(None)
    with pytest.raises(NotImplementedError):
        r.init_state()
    with pytest.raises(NotImplementedError):
        r.render(None)
    assert r.device.type == "cpu"  # no params/buffers -> defaults to cpu
