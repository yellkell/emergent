"""Gray-Scott reaction-diffusion — Turing patterns from two reagents.

Two chemicals ``U`` and ``V`` diffuse at different rates while the reaction
``U + 2V -> 3V`` consumes ``U`` and breeds ``V``. ``U`` is fed in at rate ``f``
and ``V`` is removed at rate ``f + k``::

    dU/dt = Du * lap(U) - U V^2 + f (1 - U)
    dV/dt = Dv * lap(V) + U V^2 - (f + k) V

A two-number rule (``f``, ``k``) is enough to paint coral, mitosis, fingerprints,
spirals and solitons. The Laplacian is a single convolution with a periodic
(wrap-around) world, so the whole thing is a few tensor ops per tick.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import torch
import torch.nn.functional as F

from ..core.rule import Rule
from ..render.painter import colorize

# Pearson-style (f, k) parameter bundles, with shared diffusion + dt.
# The smooth, isotropic regimes (mazes, spirals, fingerprints, coral) read as
# organic; tight "dividing spot" regimes alias into squares at this scale, so
# they are left for callers to dial in via custom (f, k).
_PRESETS: Dict[str, Dict[str, float]] = {
    "coral":      {"f": 0.0545, "k": 0.0620, "du": 0.20, "dv": 0.10, "palette": "ember"},
    "fingerprint":{"f": 0.0370, "k": 0.0600, "palette": "abyss"},
    "labyrinth":  {"f": 0.0290, "k": 0.0570, "palette": "viridis"},
    "spirals":    {"f": 0.0180, "k": 0.0510, "palette": "spectral"},
}

# 9-point isotropic Laplacian (sums to zero) for smooth, direction-free growth.
_LAPLACIAN = torch.tensor(
    [[0.05, 0.20, 0.05],
     [0.20, -1.00, 0.20],
     [0.05, 0.20, 0.05]],
    dtype=torch.float32,
).view(1, 1, 3, 3)


class GrayScott(Rule):
    name = "gray-scott"
    description = "reaction-diffusion Turing patterns"
    presets = _PRESETS
    default_preset = "coral"

    def __init__(
        self,
        size: int = 256,
        f: float = 0.0545,
        k: float = 0.0620,
        du: float = 0.16,
        dv: float = 0.08,
        dt: float = 1.0,
        substeps: int = 6,
        palette: str = "ember",
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__()
        self.size = int(size)
        self.f = float(f)
        self.k = float(k)
        self.du = float(du)
        self.dv = float(dv)
        self.dt = float(dt)
        self.substeps = int(substeps)
        self.palette = palette
        self.register_buffer("lap", _LAPLACIAN.clone())
        if device is not None:
            self.to(device)

    # -- construction ------------------------------------------------------
    @classmethod
    def build(
        cls,
        preset: Optional[str] = None,
        *,
        device: Optional[torch.device] = None,
        **overrides: Any,
    ) -> "GrayScott":
        params = dict(cls.presets[preset or cls.default_preset])
        params.update(overrides)
        return cls(device=device, **params)

    def init_state(self, spots: int = 24, noise: float = 0.02) -> torch.Tensor:
        """Saturate ``U``, then sprinkle disks of ``V`` to nucleate patterns."""
        n = self.size
        dev = self.device
        u = torch.ones(n, n, device=dev)
        v = torch.zeros(n, n, device=dev)
        yy, xx = torch.meshgrid(
            torch.arange(n, device=dev), torch.arange(n, device=dev), indexing="ij"
        )
        for _ in range(spots):
            cy = torch.randint(0, n, (1,), device=dev).item()
            cx = torch.randint(0, n, (1,), device=dev).item()
            r = torch.randint(n // 24, n // 10 + 1, (1,), device=dev).item()
            disk = (yy - cy) ** 2 + (xx - cx) ** 2 < r * r
            u = torch.where(disk, torch.full_like(u, 0.5), u)
            v = torch.where(disk, torch.full_like(v, 0.25), v)
        v = v + noise * torch.rand(n, n, device=dev)
        return torch.stack([u, v], dim=0).clamp_(0.0, 1.0)

    # -- dynamics ----------------------------------------------------------
    def _lap(self, field: torch.Tensor) -> torch.Tensor:
        x = field.view(1, 1, self.size, self.size)
        x = F.pad(x, (1, 1, 1, 1), mode="circular")
        return F.conv2d(x, self.lap).view(self.size, self.size)

    def step(self, state: torch.Tensor) -> torch.Tensor:
        u, v = state[0], state[1]
        for _ in range(self.substeps):
            uvv = u * v * v
            u = u + self.dt * (self.du * self._lap(u) - uvv + self.f * (1.0 - u))
            v = v + self.dt * (self.dv * self._lap(v) + uvv - (self.f + self.k) * v)
            u = u.clamp(0.0, 1.0)
            v = v.clamp(0.0, 1.0)
        return torch.stack([u, v], dim=0)

    def render(self, state: torch.Tensor) -> np.ndarray:
        return colorize(state[1], self.palette, lo=0.0, hi=0.45, gamma=0.85)

    def info(self, state: torch.Tensor) -> Dict[str, float]:
        return {"U": float(state[0].mean()), "V": float(state[1].mean())}
