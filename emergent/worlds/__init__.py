"""The worlds, and a tiny registry to build them by name.

Each world is a :class:`~emergent.core.Rule` exposing:

* ``presets`` — a dict of named parameter bundles,
* ``build(preset=None, *, device=None, **overrides)`` — a factory classmethod.

``make(name, ...)`` wraps the built rule in a :class:`~emergent.core.Universe`.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Type

from ..core import Rule, Universe, get_device
from .gray_scott import GrayScott
from .lenia import Lenia
from .particle_life import ParticleLife
from .neural_ca import NeuralCA

WORLDS: Dict[str, Type[Rule]] = {
    GrayScott.name: GrayScott,
    Lenia.name: Lenia,
    ParticleLife.name: ParticleLife,
    NeuralCA.name: NeuralCA,
}


def list_worlds() -> List[str]:
    return list(WORLDS)


def make(
    world: str,
    *,
    preset: Optional[str] = None,
    device: str = "auto",
    seed: Optional[int] = None,
    **overrides,
) -> Universe:
    """Build a ready-to-run :class:`Universe` for ``world``."""
    if world not in WORLDS:
        raise KeyError(f"unknown world {world!r}; choose from {list_worlds()}")
    dev = get_device(device)
    rule = WORLDS[world].build(preset=preset, device=dev, **overrides)
    return Universe(rule, seed=seed)


__all__ = [
    "WORLDS",
    "make",
    "list_worlds",
    "GrayScott",
    "Lenia",
    "ParticleLife",
    "NeuralCA",
]
