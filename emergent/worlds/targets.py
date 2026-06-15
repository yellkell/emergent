"""Procedural RGBA targets for the Neural CA to grow into.

Each target is drawn at high resolution with Pillow, downsampled for clean
anti-aliased edges, and returned as a **premultiplied** RGBA tensor of shape
``(4, H, W)`` in ``[0, 1]`` (so RGB is already zero wherever alpha is zero —
exactly what the Neural CA loss expects).
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw


def _rot(points: List[Tuple[float, float]], cx: float, cy: float, ang: float):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in points]


def _heart(d: ImageDraw.ImageDraw, S: int) -> None:
    ts = np.linspace(0, 2 * math.pi, 240)
    x = 16 * np.sin(ts) ** 3
    y = 13 * np.cos(ts) - 5 * np.cos(2 * ts) - 2 * np.cos(3 * ts) - np.cos(4 * ts)
    x = (x - x.min()) / (x.max() - x.min())
    y = 1 - (y - y.min()) / (y.max() - y.min())
    pts = [(0.10 * S + 0.80 * S * xi, 0.10 * S + 0.80 * S * yi) for xi, yi in zip(x, y)]
    d.polygon(pts, fill=(230, 40, 70, 255))


def _star(d: ImageDraw.ImageDraw, S: int) -> None:
    cx = cy = S / 2
    R, r = 0.46 * S, 0.20 * S
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=(255, 196, 28, 255))


def _spiral(d: ImageDraw.ImageDraw, S: int) -> None:
    cx = cy = S / 2
    ts = np.linspace(0, 4.2 * math.pi, 600)
    rr = (ts / ts.max()) * 0.44 * S
    pts = [(cx + ri * math.cos(t), cy + ri * math.sin(t)) for t, ri in zip(ts, rr)]
    d.line(pts, fill=(40, 210, 200, 255), width=max(2, S // 22), joint="curve")


def _flower(d: ImageDraw.ImageDraw, S: int) -> None:
    cx = cy = S / 2
    petal = 0.30 * S
    for i in range(6):
        ang = i * math.pi / 3
        px, py = cx + petal * math.cos(ang), cy + petal * math.sin(ang)
        box = [px - 0.20 * S, py - 0.20 * S, px + 0.20 * S, py + 0.20 * S]
        d.ellipse(box, fill=(236, 80, 170, 255))
    d.ellipse([cx - 0.16 * S, cy - 0.16 * S, cx + 0.16 * S, cy + 0.16 * S], fill=(255, 214, 40, 255))


def _ladybug(d: ImageDraw.ImageDraw, S: int) -> None:
    cx = cy = S / 2
    d.ellipse([0.18 * S, 0.16 * S, 0.82 * S, 0.92 * S], fill=(220, 36, 44, 255))      # body
    d.ellipse([0.32 * S, 0.06 * S, 0.68 * S, 0.40 * S], fill=(20, 20, 24, 255))        # head
    d.line([cx, 0.20 * S, cx, 0.92 * S], fill=(20, 20, 24, 255), width=max(2, S // 28))  # seam
    for sx, sy in [(0.34, 0.50), (0.66, 0.50), (0.40, 0.74), (0.60, 0.74), (0.50, 0.36)]:
        rr = 0.07 * S
        d.ellipse([sx * S - rr, sy * S - rr, sx * S + rr, sy * S + rr], fill=(20, 20, 24, 255))


_TARGETS: Dict[str, Callable[[ImageDraw.ImageDraw, int], None]] = {
    "heart": _heart,
    "star": _star,
    "spiral": _spiral,
    "flower": _flower,
    "ladybug": _ladybug,
}


def list_targets() -> List[str]:
    return list(_TARGETS)


def make_target(name: str, size: int = 40, supersample: int = 8) -> torch.Tensor:
    """Return a premultiplied RGBA target tensor ``(4, size, size)`` in ``[0, 1]``."""
    if name not in _TARGETS:
        raise KeyError(f"unknown target {name!r}; choose from {list_targets()}")
    S = size * supersample
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    _TARGETS[name](ImageDraw.Draw(img), S)
    img = img.resize((size, size), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0          # (H, W, 4), straight alpha
    rgba = torch.from_numpy(arr).permute(2, 0, 1).contiguous()
    rgb, alpha = rgba[:3], rgba[3:4]
    return torch.cat([rgb * alpha, alpha], dim=0)            # premultiply RGB by alpha
