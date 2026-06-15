"""emergent — intelligence as what simple local rules do at scale.

A tiny PyTorch framework in which a :class:`~emergent.core.Universe` is nothing
more than a :class:`~emergent.core.Rule` (the *physics*) iterated over a *state*.
Hand-write the rule and you get artificial life (Lenia, Gray-Scott, Particle
Life); *learn* the rule and global form emerges from purely local computation
(Neural Cellular Automata).

Quick start
-----------
>>> from emergent import make
>>> uni = make("lenia")
>>> frames = uni.record(steps=200, every=2, scale=3)
>>> from emergent.render import save_animation
>>> save_animation(frames, "lenia.gif", fps=30)
"""
from __future__ import annotations

__version__ = "0.1.0"

from .core import Rule, Universe, get_device
from .worlds import WORLDS, make, list_worlds

__all__ = [
    "__version__",
    "Rule",
    "Universe",
    "get_device",
    "WORLDS",
    "make",
    "list_worlds",
]
