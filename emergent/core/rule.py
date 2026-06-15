"""The :class:`Rule` — the physics of a world.

A *Rule* is the only thing a world must provide. It knows how to:

* ``init_state`` — conjure an initial state (a tensor, a bundle of tensors, …),
* ``step``       — advance that state by one tick of local computation,
* ``render``     — paint a state as an ``H x W x 3`` uint8 RGB frame.

Because a Rule is a :class:`torch.nn.Module`, hand-written rules keep their
fixed kernels as *buffers* (so they move across devices for free) and learned
rules (Neural CA) keep theirs as *parameters* (so they can be trained). The
machinery that iterates a rule lives in :class:`~emergent.core.Universe`; the
rule itself is pure, local, and stateless between calls.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import torch
import torch.nn as nn


class Rule(nn.Module):
    """Base class for every world's local update rule.

    Subclasses set :attr:`name` / :attr:`description` and implement
    :meth:`init_state`, :meth:`step` and :meth:`render`.
    """

    #: short identifier used by the CLI / registry
    name: str = "rule"
    #: one-line human description
    description: str = ""

    # -- the three things a world must define -----------------------------
    def init_state(self, **kwargs: Any) -> Any:
        """Return a fresh initial state for this rule."""
        raise NotImplementedError(f"{type(self).__name__}.init_state")

    def step(self, state: Any) -> Any:
        """Advance ``state`` by exactly one tick and return the new state."""
        raise NotImplementedError(f"{type(self).__name__}.step")

    def render(self, state: Any) -> np.ndarray:
        """Paint ``state`` as a contiguous ``(H, W, 3)`` uint8 array."""
        raise NotImplementedError(f"{type(self).__name__}.render")

    # -- optional niceties -------------------------------------------------
    def info(self, state: Any) -> Dict[str, float]:
        """Scalar diagnostics about a state (mass, energy, …) for logging."""
        return {}

    @property
    def device(self) -> torch.device:
        """The device this rule's tensors live on (params first, then buffers)."""
        for p in self.parameters():
            return p.device
        for b in self.buffers():
            return b.device
        return torch.device("cpu")

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        extra = f" — {self.description}" if self.description else ""
        return f"<{type(self).__name__}:{self.name}{extra}>"
