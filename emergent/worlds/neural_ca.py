"""Neural Cellular Automata — a *learned* local rule (Mordvintsev et al., 2020).

Every cell is a 16-vector; the first four channels are premultiplied RGBA (the
part we can see), the rest are hidden "chemical" state. At every tick a cell:

1. **perceives** its 3x3 neighbourhood through fixed Sobel filters,
2. feeds that through a tiny shared network (two 1x1 convs, ~8k weights),
3. **stochastically** adds the result to itself (only ~50% of cells fire),
4. dies if no neighbour is sufficiently "alive".

The network is identical in every cell and only ever sees its neighbours — yet
trained against a target image (via a persistent sample pool, with damage thrown
in) it learns to *grow* that image from a single seed and to *regenerate* it
after you tear pieces away. Local rule in; global, robust morphogenesis out.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ..core.rule import Rule
from ..render.painter import to_uint8
from .targets import make_target

_PRESETS: Dict[str, Dict[str, Any]] = {
    "heart":   {"target": "heart"},
    "star":    {"target": "star"},
    "spiral":  {"target": "spiral"},
    "flower":  {"target": "flower"},
    "ladybug": {"target": "ladybug"},
}


def _perception_weights(channels: int) -> torch.Tensor:
    """Fixed per-channel [identity, Sobel-x, Sobel-y] filters as a grouped conv."""
    ident = torch.tensor([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=torch.float32)
    sx = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32) / 8.0
    sy = sx.t()
    filt = torch.stack([ident, sx, sy], dim=0)              # (3, 3, 3)
    return filt.repeat(channels, 1, 1).unsqueeze(1).contiguous()  # (3C, 1, 3, 3)


class NeuralCA(Rule):
    name = "neural-ca"
    description = "learned local rule that grows and regenerates a shape"
    presets = _PRESETS
    default_preset = "heart"

    def __init__(
        self,
        channels: int = 16,
        hidden: int = 128,
        size: int = 40,
        fire_rate: float = 0.5,
        alive_threshold: float = 0.1,
        target: Optional[str] = None,
        background: Tuple[int, int, int] = (16, 16, 22),
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__()
        self.channels = int(channels)
        self.hidden = int(hidden)
        self.size = int(size)
        self.fire_rate = float(fire_rate)
        self.alive_threshold = float(alive_threshold)
        self.background = background
        self.target_name = target

        self.register_buffer("perception", _perception_weights(self.channels))
        self.w1 = nn.Conv2d(3 * self.channels, self.hidden, 1)
        self.w2 = nn.Conv2d(self.hidden, self.channels, 1, bias=False)
        nn.init.zeros_(self.w2.weight)  # start as a no-op: cells do nothing until trained

        if device is not None:
            self.to(device)

    @classmethod
    def build(
        cls,
        preset: Optional[str] = None,
        *,
        device: Optional[torch.device] = None,
        **overrides: Any,
    ) -> "NeuralCA":
        params = dict(cls.presets[preset or cls.default_preset])
        params.update(overrides)
        return cls(device=device, **params)

    # -- the learned local rule -------------------------------------------
    def perceive(self, x: torch.Tensor) -> torch.Tensor:
        return F.conv2d(x, self.perception, padding=1, groups=self.channels)

    def alive(self, x: torch.Tensor) -> torch.Tensor:
        alpha = x[:, 3:4]
        return F.max_pool2d(alpha, 3, stride=1, padding=1) > self.alive_threshold

    def update(self, x: torch.Tensor) -> torch.Tensor:
        """One tick of the CA on a batched grid ``(B, C, H, W)``."""
        pre_life = self.alive(x)
        dx = self.w2(torch.relu(self.w1(self.perceive(x))))
        if self.fire_rate < 1.0:
            mask = (torch.rand_like(x[:, :1]) < self.fire_rate).float()
            dx = dx * mask
        x = x + dx
        life = (pre_life & self.alive(x)).float()
        return x * life

    # -- states ------------------------------------------------------------
    def seed(self, batch: int = 1) -> torch.Tensor:
        """A single living cell at the centre (alpha + hidden = 1, RGB = 0)."""
        z = torch.zeros(batch, self.channels, self.size, self.size, device=self.device)
        z[:, 3:, self.size // 2, self.size // 2] = 1.0
        return z

    def init_state(self, **kwargs: Any) -> torch.Tensor:
        return self.seed(1)

    def step(self, state: torch.Tensor) -> torch.Tensor:
        return self.update(state)

    def damage(self, state: torch.Tensor, where: Optional[Tuple[float, float]] = None,
               radius: float = 0.35) -> torch.Tensor:
        """Zero out a circular region — the wound a regenerating CA must heal."""
        b, c, h, w = state.shape
        if where is None:
            cy, cx = torch.rand(2).tolist()
        else:
            cy, cx = where
        ys = torch.arange(h, device=state.device).view(h, 1) / h
        xs = torch.arange(w, device=state.device).view(1, w) / w
        keep = ((ys - cy) ** 2 + (xs - cx) ** 2) > radius ** 2
        return state * keep.view(1, 1, h, w)

    # -- rendering ---------------------------------------------------------
    def render(self, state: torch.Tensor) -> np.ndarray:
        x = state[0]
        rgb = x[:3].clamp(0.0, 1.0).permute(1, 2, 0)          # premultiplied
        alpha = x[3:4].clamp(0.0, 1.0).permute(1, 2, 0)
        bg = torch.tensor(self.background, dtype=torch.float32, device=x.device) / 255.0
        out = rgb + bg * (1.0 - alpha)
        return to_uint8(out)

    def info(self, state: torch.Tensor) -> Dict[str, float]:
        return {"alpha": float(state[0, 3].mean()), "alive": float((state[0, 3] > 0.1).float().mean())}

    # -- training (the part that makes the rule "intelligent") ------------
    def fit(
        self,
        target: torch.Tensor,
        *,
        iters: int = 1200,
        batch: int = 8,
        pool_size: int = 1024,
        lr: float = 2e-3,
        step_range: Tuple[int, int] = (48, 64),
        damage: bool = True,
        n_damage: int = 2,
        n_seed: int = 1,
        lr_decay_at: float = 0.7,
        log_every: int = 50,
        on_log: Optional[Callable[[int, float], None]] = None,
    ) -> List[float]:
        """Learn the local rule that grows ``target`` and heals damage.

        Uses a persistent **sample pool**: most batches continue from where a
        previous rollout left off (teaching persistence), the worst sample is
        re-seeded each step (teaching growth-from-scratch), and a few well-grown
        samples are damaged (teaching regeneration).
        """
        dev = self.device
        self.train()
        tgt = target.to(dev).unsqueeze(0)                      # (1, 4, H, W)
        pool = self.seed(pool_size)                            # (P, C, H, W)
        opt = torch.optim.Adam(self.parameters(), lr=lr)
        sched = torch.optim.lr_scheduler.MultiStepLR(
            opt, milestones=[int(iters * lr_decay_at)], gamma=0.1
        )
        history: List[float] = []

        for it in range(iters):
            idx = torch.randperm(pool_size, device=dev)[:batch]
            x = pool[idx].clone()

            # Rank by current loss: re-seed the worst (so growth-from-scratch is
            # always in the batch and weighted enough to actually be learned),
            # damage the best (so regeneration is learned).
            with torch.no_grad():
                rank = ((x[:, :4] - tgt) ** 2).mean(dim=(1, 2, 3)).argsort(descending=True)
            seeds = max(1, min(n_seed, batch - 1))
            for s in range(seeds):
                x[rank[s]] = self.seed(1)[0]
            if damage and it > iters // 20:
                for j in range(1, 1 + min(n_damage, batch - seeds)):
                    x[rank[-j]] = self.damage(x[rank[-j]].unsqueeze(0))[0]

            steps = int(torch.randint(step_range[0], step_range[1] + 1, (1,)).item())
            for _ in range(steps):
                x = self.update(x)

            loss = ((x[:, :4] - tgt) ** 2).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            for p in self.parameters():                        # normalise grads for stability
                if p.grad is not None:
                    p.grad /= p.grad.norm() + 1e-8
            opt.step()
            sched.step()

            pool[idx] = x.detach()
            history.append(float(loss.detach()))
            if (it % log_every == 0 or it == iters - 1) and on_log is not None:
                on_log(it, history[-1])

        self.eval()
        return history

    # -- persistence -------------------------------------------------------
    def save(self, path: str) -> str:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        torch.save(
            {
                "state_dict": self.state_dict(),
                "channels": self.channels,
                "hidden": self.hidden,
                "size": self.size,
                "fire_rate": self.fire_rate,
                "target_name": self.target_name,
                "background": self.background,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: str, device: Optional[torch.device] = None) -> "NeuralCA":
        ckpt = torch.load(path, map_location=device or "cpu", weights_only=False)
        model = cls(
            channels=ckpt["channels"],
            hidden=ckpt["hidden"],
            size=ckpt["size"],
            fire_rate=ckpt["fire_rate"],
            target=ckpt.get("target_name"),
            background=tuple(ckpt.get("background", (16, 16, 22))),
            device=device,
        )
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        return model


def train_nca(
    target: str = "heart",
    *,
    size: int = 40,
    device: Optional[torch.device] = None,
    on_log: Optional[Callable[[int, float], None]] = None,
    **fit_kwargs: Any,
) -> Tuple[NeuralCA, List[float]]:
    """Build a Neural CA and train it to grow ``target``. Returns (model, loss history)."""
    model = NeuralCA(size=size, target=target, device=device)
    tgt = make_target(target, size=size)
    history = model.fit(tgt, on_log=on_log, **fit_kwargs)
    return model, history
