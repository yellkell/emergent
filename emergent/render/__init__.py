"""Rendering: turn fields and particles into colour, then into files."""
from __future__ import annotations

from .palettes import PALETTES, get_palette, list_palettes
from .painter import (
    alpha_over,
    colorize,
    montage,
    to_uint8,
    upscale,
)
from .recorder import save_animation, save_image

__all__ = [
    "PALETTES",
    "get_palette",
    "list_palettes",
    "colorize",
    "upscale",
    "to_uint8",
    "alpha_over",
    "montage",
    "save_animation",
    "save_image",
]
