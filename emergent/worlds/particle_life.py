"""Particle Life — emergent organisms from an asymmetric attraction matrix.

Every particle belongs to one of ``K`` species. The *entire* rule is a ``K x K``
matrix ``A``: ``A[i, j]`` says how strongly a particle of species ``i`` is drawn
to (``+``) or repelled by (``-``) a particle of species ``j`` within a short
range. Below a hard core every pair repels (so matter never collapses to a
point). Out of this two-line force law, cells, membranes, gliders, chasers and
whole ecologies appear — none of it written down anywhere but the matrix.
"""
from __future__ import annotations

import colorsys
from typing import Any, Dict, Optional

import numpy as np
import torch

from ..core.rule import Rule
from ..render.painter import to_uint8

State = Dict[str, torch.Tensor]

_PRESETS: Dict[str, Dict[str, Any]] = {
    "ecology":  {"n": 1200, "species": 6, "rmax": 0.10, "beta": 0.30,
                 "force": 4.0, "friction_half_life": 0.040, "dt": 0.02},
    "cells":    {"n": 1000, "species": 4, "rmax": 0.12, "beta": 0.25,
                 "force": 5.0, "friction_half_life": 0.030, "dt": 0.02},
    "swarm":    {"n": 1500, "species": 3, "rmax": 0.08, "beta": 0.35,
                 "force": 3.0, "friction_half_life": 0.050, "dt": 0.02},
    "gliders":  {"n": 900,  "species": 5, "rmax": 0.10, "beta": 0.30,
                 "force": 6.0, "friction_half_life": 0.025, "dt": 0.02},
}


def _species_colors(k: int) -> np.ndarray:
    """``k`` bright, evenly-spaced hues as ``(k, 3)`` floats in ``[0, 1]``."""
    cols = [colorsys.hsv_to_rgb(i / k, 0.85, 1.0) for i in range(k)]
    return np.asarray(cols, dtype=np.float32)


class ParticleLife(Rule):
    name = "particle-life"
    description = "self-organising particle ecologies"
    presets = _PRESETS
    default_preset = "ecology"

    def __init__(
        self,
        n: int = 1200,
        species: int = 6,
        rmax: float = 0.10,
        beta: float = 0.30,
        force: float = 4.0,
        friction_half_life: float = 0.040,
        dt: float = 0.02,
        size: int = 320,
        glow: float = 1.6,
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__()
        self.n = int(n)
        self.species = int(species)
        self.rmax = float(rmax)
        self.beta = float(beta)
        self.force = float(force)
        self.dt = float(dt)
        self.friction = float(0.5 ** (dt / friction_half_life))
        self.size = int(size)
        self.glow = float(glow)
        # The whole "rule": a random asymmetric interaction matrix in [-1, 1].
        self.register_buffer("matrix", torch.empty(self.species, self.species).uniform_(-1.0, 1.0))
        self.register_buffer("colors", torch.from_numpy(_species_colors(self.species)))
        if device is not None:
            self.to(device)

    @classmethod
    def build(
        cls,
        preset: Optional[str] = None,
        *,
        device: Optional[torch.device] = None,
        **overrides: Any,
    ) -> "ParticleLife":
        params = dict(cls.presets[preset or cls.default_preset])
        params.update(overrides)
        return cls(device=device, **params)

    # -- state -------------------------------------------------------------
    def init_state(self, **kwargs: Any) -> State:
        dev = self.device
        pos = torch.rand(self.n, 2, device=dev)
        vel = torch.zeros(self.n, 2, device=dev)
        types = torch.randint(0, self.species, (self.n,), device=dev)
        return {"pos": pos, "vel": vel, "types": types}

    # -- dynamics ----------------------------------------------------------
    def step(self, state: State) -> State:
        pos, vel, types = state["pos"], state["vel"], state["types"]
        # Pairwise displacement with the minimum-image convention (torus world).
        diff = pos.unsqueeze(0) - pos.unsqueeze(1)      # (N, N, 2): i -> j
        diff = diff - torch.round(diff)                  # wrap into [-0.5, 0.5)
        dist = torch.linalg.vector_norm(diff, dim=-1)    # (N, N)
        r = dist / self.rmax

        a = self.matrix[types.unsqueeze(1), types.unsqueeze(0)]  # (N, N) per-pair affinity
        close = r < self.beta
        mid = (r >= self.beta) & (r < 1.0)
        f = torch.zeros_like(r)
        f = torch.where(close, r / self.beta - 1.0, f)                       # hard-core repulsion
        f = torch.where(mid, a * (1.0 - torch.abs(2.0 * r - 1.0 - self.beta) / (1.0 - self.beta)), f)
        f = f * (dist > 0)                                                   # ignore self-pair

        unit = diff / dist.clamp_min(1e-9).unsqueeze(-1)
        accel = (f.unsqueeze(-1) * unit).sum(dim=1) * self.rmax * self.force

        vel = vel * self.friction + accel * self.dt
        pos = (pos + vel * self.dt) % 1.0
        return {"pos": pos, "vel": vel, "types": types}

    # -- rendering ---------------------------------------------------------
    def render(self, state: State) -> np.ndarray:
        s = self.size
        pos, types = state["pos"], state["types"]
        canvas = torch.zeros(3, s * s, device=pos.device)
        px = (pos[:, 0] * s).long().clamp_(0, s - 1)
        py = (pos[:, 1] * s).long().clamp_(0, s - 1)
        cols = self.colors[types].t().contiguous()       # (3, N)

        rad = 2
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                w = float(np.exp(-(dx * dx + dy * dy) / (2.0 * 1.1 ** 2)))
                xi = (px + dx) % s
                yi = (py + dy) % s
                idx = yi * s + xi
                canvas.index_add_(1, idx, cols * w)

        img = canvas.view(3, s, s)
        img = 1.0 - torch.exp(-self.glow * img)          # soft glow tone-map
        rgb = img.permute(1, 2, 0).contiguous()
        return to_uint8(rgb)

    def info(self, state: State) -> Dict[str, float]:
        speed = torch.linalg.vector_norm(state["vel"], dim=-1).mean()
        return {"speed": float(speed)}
