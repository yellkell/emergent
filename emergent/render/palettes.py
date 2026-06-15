"""Perceptual colour palettes as 256-entry lookup tables — no matplotlib.

Each palette is defined by a handful of anchor colours which we linearly
interpolate (in sRGB, good enough for art) into a ``(256, 3)`` uint8 table.
The anchors for the scientific maps are sampled from their canonical
definitions; the rest are hand-tuned for these particular worlds.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Tuple

import numpy as np

# Anchor colours, evenly spaced from 0 -> 1, as 0..255 RGB triples.
_ANCHORS: Dict[str, List[Tuple[int, int, int]]] = {
    # --- scientific (sampled from the canonical colormaps) ---
    "viridis": [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)],
    "magma":   [(0, 0, 4), (80, 18, 123), (182, 54, 121), (251, 136, 97), (252, 253, 191)],
    "inferno": [(0, 0, 4), (87, 16, 110), (188, 55, 84), (249, 142, 9), (252, 255, 164)],
    "plasma":  [(13, 8, 135), (126, 3, 168), (204, 71, 120), (248, 149, 64), (240, 249, 33)],
    "turbo":   [(48, 18, 59), (28, 162, 221), (96, 221, 67), (251, 160, 38), (122, 4, 3)],
    # --- hand-tuned for these worlds ---
    "ember":   [(2, 0, 4), (40, 4, 30), (140, 18, 40), (240, 96, 24), (255, 214, 120), (255, 255, 244)],
    "abyss":   [(2, 4, 16), (8, 28, 64), (10, 78, 120), (24, 158, 158), (130, 230, 200), (240, 255, 240)],
    "spectral":[(20, 0, 40), (60, 10, 120), (10, 110, 200), (10, 200, 160), (180, 235, 60), (255, 240, 120)],
    "bloom":   [(8, 2, 20), (70, 10, 90), (170, 30, 120), (240, 90, 120), (255, 170, 120), (255, 240, 210)],
    "ice":     [(4, 6, 18), (16, 40, 80), (40, 110, 170), (120, 190, 230), (220, 245, 255)],
    "mono":    [(0, 0, 0), (255, 255, 255)],
}


@lru_cache(maxsize=None)
def get_palette(name: str) -> np.ndarray:
    """Return a ``(256, 3)`` uint8 lookup table for ``name``."""
    try:
        anchors = _ANCHORS[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(
            f"unknown palette {name!r}; choose from {sorted(_ANCHORS)}"
        ) from exc
    anchors_arr = np.asarray(anchors, dtype=np.float64)
    n = len(anchors_arr)
    xs = np.linspace(0.0, 1.0, n)
    grid = np.linspace(0.0, 1.0, 256)
    lut = np.empty((256, 3), dtype=np.float64)
    for c in range(3):
        lut[:, c] = np.interp(grid, xs, anchors_arr[:, c])
    return np.clip(np.round(lut), 0, 255).astype(np.uint8)


def list_palettes() -> List[str]:
    return sorted(_ANCHORS)


# Eagerly expose the names (tables themselves are built lazily + cached).
PALETTES: List[str] = list_palettes()
