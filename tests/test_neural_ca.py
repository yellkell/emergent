import numpy as np
import torch

from emergent.worlds.neural_ca import NeuralCA
from emergent.worlds.targets import list_targets, make_target


def test_targets_are_premultiplied_and_bounded():
    for name in list_targets():
        t = make_target(name, size=16)
        assert t.shape == (4, 16, 16)
        assert float(t.min()) >= 0.0 and float(t.max()) <= 1.0 + 1e-6
        rgb, alpha = t[:3], t[3:4]
        # premultiplied alpha => every colour channel is bounded by alpha
        assert bool((rgb <= alpha + 1e-5).all())


def test_seed_has_exactly_one_living_cell():
    m = NeuralCA(size=16)
    s = m.seed(1)
    assert s.shape == (1, m.channels, 16, 16)
    assert int((s[0, 3] > 0.1).sum()) == 1


def test_untrained_step_is_noop_but_shape_stable():
    m = NeuralCA(size=16)  # w2 zero-init => update adds nothing
    s = m.seed(1)
    s2 = m.step(s)
    assert s2.shape == s.shape
    assert torch.allclose(s2, s)


def test_damage_removes_mass():
    m = NeuralCA(size=24)
    x = torch.ones(1, m.channels, 24, 24)
    wounded = m.damage(x, where=(0.5, 0.5), radius=0.4)
    assert float(wounded.sum()) < float(x.sum())


def test_fit_reduces_loss_and_checkpoint_roundtrips(tmp_path):
    torch.manual_seed(0)
    m = NeuralCA(size=20, hidden=48)
    target = make_target("heart", size=20)
    hist = m.fit(target, iters=40, batch=4, step_range=(24, 32), log_every=100)
    assert min(hist) < hist[0]  # it learns *something*

    path = m.save(str(tmp_path / "m.pt"))
    m2 = NeuralCA.load(path)
    assert m2.size == m.size and m2.hidden == m.hidden
    for p, q in zip(m.parameters(), m2.parameters()):
        assert torch.allclose(p, q)
    out = m2.render(m2.seed(1))
    assert out.dtype == np.uint8 and out.shape == (20, 20, 3)
