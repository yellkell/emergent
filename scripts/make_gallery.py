"""Render the curated gallery referenced by the README.

Run from the repo root *after* the Neural CA checkpoints exist::

    python scripts/train_gallery_nca.py   # produces checkpoints/*.pt
    python scripts/make_gallery.py        # produces gallery/*

Hand-written worlds are rendered fresh; Neural CA clips are regenerated from
their checkpoints so every GIF uses the current (correct-timing) recorder.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emergent import make
from emergent.cli import _render_growth
from emergent.render import montage, save_animation, save_image
from emergent.worlds.neural_ca import NeuralCA
from emergent.worlds.targets import list_targets

OUT = "gallery"
TILE = 256


def _resize(frame: np.ndarray, px: int = TILE) -> np.ndarray:
    return np.asarray(Image.fromarray(frame[..., :3]).resize((px, px), Image.NEAREST))


def hero(world, preset, steps, *, size=None, png=True, **ov):
    kw = {} if size is None else {"size": size}
    uni = make(world, preset=preset, seed=0, **kw, **ov)
    uni.step(steps)
    frame = uni.rule.render(uni.state)
    if png:
        save_image(_resize(frame), os.path.join(OUT, f"{world}_{preset}.png"))
    print(f"  hero  {world}_{preset}.png")
    return frame


def clip(world, preset, *, steps, every, scale, size=None, fps=30, **ov):
    kw = {} if size is None else {"size": size}
    uni = make(world, preset=preset, seed=0, **kw, **ov)
    frames = uni.record(steps, every=every, scale=scale)
    path = os.path.join(OUT, f"{world}_{preset}.gif")
    save_animation(frames, path, fps=fps)
    print(f"  clip  {os.path.basename(path)}  ({len(frames)} frames)")
    return frames


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    print("rendering hand-written worlds…")
    f_coral = hero("gray-scott", "coral", 420, size=200)
    f_finger = hero("gray-scott", "fingerprint", 620, size=200)
    hero("gray-scott", "spirals", 720, size=200)
    hero("lenia", "orbium", 240, size=140)
    f_cells = hero("particle-life", "cells", 360)

    gem = clip("lenia", "geminium", steps=300, every=2, scale=2, size=140, fps=30)
    clip("particle-life", "ecology", steps=330, every=3, scale=1, size=260, fps=24)

    print("regenerating neural-ca clips from checkpoints…")
    nca_frame = None
    for target in list_targets():
        ckpt = os.path.join("checkpoints", f"{target}.pt")
        if not os.path.exists(ckpt):
            continue
        model = NeuralCA.load(ckpt)
        _render_growth(model, os.path.join(OUT, f"neural-ca_{target}.gif"),
                       steps=130, scale=5, damage=True, fps=18)
        if nca_frame is None:
            import torch
            from emergent.core import Universe
            torch.manual_seed(0)
            u = Universe(model)
            u.step(96)  # a fully grown organism for the montage
            nca_frame = model.render(u.state)

    print("composing montage…")
    tiles = [f_coral, f_finger, gem[len(gem) // 2], f_cells]
    if nca_frame is not None:
        tiles.append(nca_frame)
    tiles = [_resize(t) for t in tiles]
    save_image(montage(tiles, cols=len(tiles), pad=6), os.path.join(OUT, "montage.png"))
    print(f"  montage.png ({len(tiles)} tiles)")
    print("gallery complete →", OUT)


if __name__ == "__main__":
    main()
