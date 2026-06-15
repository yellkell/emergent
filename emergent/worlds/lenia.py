"""Lenia — a continuous cellular automaton (Bert Wang-Chak Chan, 2018).

Where Conway's Life is a binary grid updated by counting neighbours, Lenia is a
*smooth* field ``A`` in ``[0, 1]`` updated by one convolution and one bell curve::

    U = K * A                       # potential: how much "neighbourhood" each cell feels
    A <- clip(A + dt * G(U), 0, 1)  # grow toward, or decay away from, a target density

``K`` is a soft radial kernel (one or several concentric rings) and the growth
map ``G(u) = 2 exp(-(u-mu)^2 / 2 sigma^2) - 1`` rewards cells whose neighbourhood
density sits near ``mu``. From this, gliders, rotors and lifelike "creatures"
self-organise out of noise.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn.functional as F

from ..core.rule import Rule
from ..render.painter import colorize

# Parameter bundles. ``betas`` are the relative heights of the kernel's
# concentric rings (one entry == a single ring).
_PRESETS: Dict[str, Dict[str, Any]] = {
    "orbium":   {"R": 13, "mu": 0.150, "sigma": 0.017, "dt": 0.10,
                 "betas": [1.0], "palette": "abyss", "seed_kind": "soup"},
    "geminium": {"R": 18, "mu": 0.260, "sigma": 0.036, "dt": 0.10,
                 "betas": [0.5, 1.0, 0.667], "palette": "spectral", "seed_kind": "soup"},
    "fluid":    {"R": 16, "mu": 0.140, "sigma": 0.014, "dt": 0.10,
                 "betas": [1.0, 0.4], "palette": "ice", "seed_kind": "soup"},
    "coral":    {"R": 20, "mu": 0.160, "sigma": 0.018, "dt": 0.10,
                 "betas": [1.0, 0.333], "palette": "bloom", "seed_kind": "patch"},
}


def _build_kernel(R: int, betas: List[float], sigma_k: float = 0.15) -> np.ndarray:
    """A normalised radial kernel of size ``(2R+1, 2R+1)``."""
    size = 2 * R + 1
    ax = np.arange(size, dtype=np.float64) - R
    xx, yy = np.meshgrid(ax, ax)
    dist = np.sqrt(xx * xx + yy * yy) / R  # 0 at centre, 1 at radius R
    k = len(betas)
    kernel = np.zeros_like(dist)
    mask = dist < 1.0
    r = dist[mask]
    ring = np.minimum((r * k).astype(int), k - 1)
    heights = np.asarray(betas, dtype=np.float64)[ring]
    pos = (r * k) % 1.0  # position within the cell's ring, in [0, 1)
    kernel[mask] = heights * np.exp(-((pos - 0.5) ** 2) / (2.0 * sigma_k ** 2))
    total = kernel.sum()
    if total > 0:
        kernel /= total
    return kernel


class Lenia(Rule):
    name = "lenia"
    description = "continuous cellular automaton (artificial life)"
    presets = _PRESETS
    default_preset = "orbium"

    def __init__(
        self,
        size: int = 160,
        R: int = 13,
        mu: float = 0.15,
        sigma: float = 0.017,
        dt: float = 0.10,
        betas: Optional[List[float]] = None,
        sigma_k: float = 0.15,
        palette: str = "abyss",
        seed_kind: str = "soup",
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__()
        self.size = int(size)
        self.R = int(R)
        self.mu = float(mu)
        self.sigma = float(sigma)
        self.dt = float(dt)
        self.palette = palette
        self.seed_kind = seed_kind
        betas = list(betas) if betas else [1.0]
        kernel = _build_kernel(self.R, betas, sigma_k)
        self.register_buffer(
            "kernel", torch.from_numpy(kernel).float().view(1, 1, *kernel.shape)
        )
        if device is not None:
            self.to(device)

    @classmethod
    def build(
        cls,
        preset: Optional[str] = None,
        *,
        device: Optional[torch.device] = None,
        **overrides: Any,
    ) -> "Lenia":
        params = dict(cls.presets[preset or cls.default_preset])
        params.update(overrides)
        return cls(device=device, **params)

    # -- seeding -----------------------------------------------------------
    def init_state(self, **kwargs: Any) -> torch.Tensor:
        n, dev = self.size, self.device
        kind = kwargs.get("seed_kind", self.seed_kind)
        if kind == "patch":
            a = torch.zeros(n, n, device=dev)
            w = n // 3
            lo = (n - w) // 2
            a[lo : lo + w, lo : lo + w] = torch.rand(w, w, device=dev)
            return a
        if kind == "blobs":
            a = torch.zeros(n, n, device=dev)
            yy, xx = torch.meshgrid(
                torch.arange(n, device=dev), torch.arange(n, device=dev), indexing="ij"
            )
            for _ in range(6):
                cy, cx = (torch.randint(0, n, (2,), device=dev)).tolist()
                r = self.R * (1.2 + torch.rand(1, device=dev).item())
                blob = torch.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * r * r))
                a = torch.clamp(a + blob * torch.rand(1, device=dev).item(), 0, 1)
            return a
        # "soup": full-field smoothed noise (then masked to a central disk)
        a = torch.rand(n, n, device=dev)
        a = self._smooth(a, passes=2)
        yy, xx = torch.meshgrid(
            torch.arange(n, device=dev), torch.arange(n, device=dev), indexing="ij"
        )
        disk = ((yy - n / 2) ** 2 + (xx - n / 2) ** 2) < (0.42 * n) ** 2
        a = torch.where(disk, a, torch.zeros_like(a))
        return (a - a.min()) / (a.max() - a.min() + 1e-9)

    def _smooth(self, x: torch.Tensor, passes: int = 1) -> torch.Tensor:
        ker = torch.ones(1, 1, 3, 3, device=x.device) / 9.0
        y = x.view(1, 1, *x.shape)
        for _ in range(passes):
            y = F.conv2d(F.pad(y, (1, 1, 1, 1), mode="circular"), ker)
        return y.view(*x.shape)

    # -- dynamics ----------------------------------------------------------
    def _growth(self, u: torch.Tensor) -> torch.Tensor:
        return 2.0 * torch.exp(-((u - self.mu) ** 2) / (2.0 * self.sigma ** 2)) - 1.0

    def step(self, state: torch.Tensor) -> torch.Tensor:
        R = self.R
        x = state.view(1, 1, self.size, self.size)
        x = F.pad(x, (R, R, R, R), mode="circular")
        u = F.conv2d(x, self.kernel).view(self.size, self.size)
        return (state + self.dt * self._growth(u)).clamp(0.0, 1.0)

    def render(self, state: torch.Tensor) -> np.ndarray:
        return colorize(state, self.palette, lo=0.0, hi=1.0, gamma=0.9)

    def info(self, state: torch.Tensor) -> Dict[str, float]:
        return {"mass": float(state.mean()), "max": float(state.max())}
