import os

import numpy as np
import pytest

from emergent.render import (
    alpha_over,
    colorize,
    get_palette,
    list_palettes,
    montage,
    save_animation,
    save_image,
    to_uint8,
    upscale,
)


def test_every_palette_builds():
    for name in list_palettes():
        lut = get_palette(name)
        assert lut.shape == (256, 3)
        assert lut.dtype == np.uint8


def test_colorize_shape_and_range():
    field = np.linspace(0, 1, 64).reshape(8, 8)
    img = colorize(field, "viridis")
    assert img.shape == (8, 8, 3)
    assert img.dtype == np.uint8


def test_colorize_constant_field_is_safe():
    img = colorize(np.zeros((5, 5)), "magma")  # zero span must not divide by zero
    assert img.shape == (5, 5, 3)


def test_to_uint8_roundtrip():
    arr = np.array([[0.0, 0.5, 1.0]])
    out = to_uint8(arr)
    assert out.dtype == np.uint8
    assert list(out[0]) == [0, 128, 255]


def test_upscale():
    img = np.zeros((4, 4, 3), np.uint8)
    assert upscale(img, 3).shape == (12, 12, 3)
    assert upscale(img, 1) is img


def test_alpha_over_opaque_returns_foreground():
    rgb = np.ones((4, 4, 3))
    out = alpha_over(rgb, np.ones((4, 4)), (0, 0, 0))
    assert (out == 255).all()


def test_montage_grid():
    frames = [np.full((4, 4, 3), i, np.uint8) for i in range(5)]
    m = montage(frames, cols=2, pad=1)
    assert m.ndim == 3 and m.shape[2] == 3


def test_save_animation_and_image(tmp_path):
    rng = np.random.default_rng(0)
    frames = [(rng.random((10, 10, 3)) * 255).astype(np.uint8) for _ in range(5)]
    gif = save_animation(frames, str(tmp_path / "a.gif"), fps=10)
    mp4 = save_animation(frames, str(tmp_path / "a.mp4"), fps=10)
    png = save_image(frames[0], str(tmp_path / "a.png"))
    for p in (gif, mp4, png):
        assert os.path.exists(p) and os.path.getsize(p) > 0


def test_save_animation_rejects_empty(tmp_path):
    with pytest.raises(ValueError):
        save_animation([], str(tmp_path / "x.gif"))
