"""Painter: scalar fields and RGBA layers -> uint8 RGB frames."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

from .palettes import get_palette

try:  # torch is a hard dep of the project, but keep painter import-light
    import torch

    _Tensorish = Union[np.ndarray, "torch.Tensor"]
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    _Tensorish = np.ndarray  # type: ignore


def _to_numpy(x: _Tensorish) -> np.ndarray:
    if torch is not None and isinstance(x, torch.Tensor):
        return x.detach().to("cpu").float().numpy()
    return np.asarray(x)


def to_uint8(x: _Tensorish) -> np.ndarray:
    """Coerce floats in ``[0, 1]`` (or existing uint8) to a uint8 array."""
    arr = _to_numpy(x)
    if arr.dtype == np.uint8:
        return arr
    return np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8)


def colorize(
    field: _Tensorish,
    palette: str = "magma",
    *,
    lo: Optional[float] = None,
    hi: Optional[float] = None,
    gamma: float = 1.0,
) -> np.ndarray:
    """Map a 2-D scalar ``field`` to an ``(H, W, 3)`` uint8 RGB image.

    ``lo``/``hi`` set the normalisation window (defaults to the field's own
    min/max); ``gamma`` < 1 lifts shadows, > 1 deepens them.
    """
    arr = _to_numpy(field).astype(np.float64)
    if arr.ndim != 2:
        raise ValueError(f"colorize expects a 2-D field, got shape {arr.shape}")
    lo_v = float(np.min(arr)) if lo is None else float(lo)
    hi_v = float(np.max(arr)) if hi is None else float(hi)
    span = hi_v - lo_v
    if span <= 1e-12:
        norm = np.zeros_like(arr)
    else:
        norm = np.clip((arr - lo_v) / span, 0.0, 1.0)
    if gamma != 1.0:
        norm = np.power(norm, gamma)
    idx = np.clip(np.round(norm * 255.0), 0, 255).astype(np.intp)
    return get_palette(palette)[idx]


def upscale(img: np.ndarray, factor: int) -> np.ndarray:
    """Nearest-neighbour integer upscale of an ``H x W`` or ``H x W x C`` image."""
    if factor == 1:
        return img
    if factor < 1:
        raise ValueError("factor must be >= 1")
    return np.repeat(np.repeat(img, factor, axis=0), factor, axis=1)


def alpha_over(
    rgb: _Tensorish,
    alpha: _Tensorish,
    background: Tuple[int, int, int] = (8, 8, 12),
) -> np.ndarray:
    """Composite an ``H x W x 3`` colour layer over a flat ``background``.

    ``rgb`` and ``alpha`` are floats in ``[0, 1]``; alpha is the per-pixel
    opacity. Returns uint8 RGB.
    """
    fg = np.clip(_to_numpy(rgb).astype(np.float64), 0.0, 1.0)
    a = np.clip(_to_numpy(alpha).astype(np.float64), 0.0, 1.0)
    if a.ndim == 2:
        a = a[..., None]
    bg = np.asarray(background, dtype=np.float64) / 255.0
    out = fg * a + bg * (1.0 - a)
    return np.clip(np.round(out * 255.0), 0, 255).astype(np.uint8)


def montage(
    frames: Sequence[np.ndarray],
    cols: Optional[int] = None,
    pad: int = 4,
    background: Tuple[int, int, int] = (12, 12, 16),
) -> np.ndarray:
    """Tile equal-sized RGB frames into a single padded grid image."""
    if not frames:
        raise ValueError("montage needs at least one frame")
    h, w = frames[0].shape[:2]
    n = len(frames)
    cols = cols or int(np.ceil(np.sqrt(n)))
    rows = int(np.ceil(n / cols))
    H = rows * h + (rows + 1) * pad
    W = cols * w + (cols + 1) * pad
    canvas = np.empty((H, W, 3), dtype=np.uint8)
    canvas[:] = np.asarray(background, dtype=np.uint8)
    for i, frame in enumerate(frames):
        r, c = divmod(i, cols)
        y = pad + r * (h + pad)
        x = pad + c * (w + pad)
        canvas[y : y + h, x : x + w] = frame[..., :3]
    return canvas
