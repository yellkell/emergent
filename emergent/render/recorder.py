"""Recorder: write frame sequences to GIF/MP4 and single images to PNG."""
from __future__ import annotations

import os
from typing import Sequence

import numpy as np

import imageio.v2 as imageio


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


def save_image(frame: np.ndarray, path: str) -> str:
    """Write a single ``H x W x 3`` uint8 frame to ``path`` (PNG/JPG/…)."""
    _ensure_parent(path)
    imageio.imwrite(path, np.ascontiguousarray(frame[..., :3]))
    return path


def save_animation(
    frames: Sequence[np.ndarray],
    path: str,
    *,
    fps: int = 30,
    loop: int = 0,
    quality: int = 8,
) -> str:
    """Write ``frames`` to an animation, dispatching on file extension.

    ``.gif`` uses the Pillow plugin (``loop=0`` loops forever); ``.mp4``/``.webm``
    use the bundled ffmpeg. Frames are coerced to contiguous uint8 RGB.
    """
    if len(frames) == 0:
        raise ValueError("save_animation got zero frames")
    _ensure_parent(path)
    ext = os.path.splitext(path)[1].lower()
    clean = [np.ascontiguousarray(np.asarray(f)[..., :3].astype(np.uint8)) for f in frames]

    if ext == ".gif":
        # Modern Pillow plugin wants per-frame duration in milliseconds.
        imageio.mimsave(path, clean, format="GIF", duration=1000.0 / fps, loop=loop)
    elif ext in {".mp4", ".webm", ".mkv", ".mov"}:
        # yuv420p + even dimensions keeps the output playable everywhere.
        even = [_pad_even(f) for f in clean]
        imageio.mimsave(
            path,
            even,
            fps=fps,
            quality=quality,
            macro_block_size=None,
            output_params=["-pix_fmt", "yuv420p"],
        )
    else:
        raise ValueError(f"unsupported animation extension: {ext!r}")
    return path


def _pad_even(frame: np.ndarray) -> np.ndarray:
    """Pad height/width up to even numbers (h.264 requires it)."""
    h, w = frame.shape[:2]
    ph, pw = h % 2, w % 2
    if not (ph or pw):
        return frame
    return np.pad(frame, ((0, ph), (0, pw), (0, 0)), mode="edge")
