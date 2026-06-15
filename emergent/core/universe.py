"""The :class:`Universe` — a rule, a state, and the arrow of time.

Everything interesting happens inside a :class:`Rule`; the Universe just turns
the crank. It owns the current state, advances it, and (lazily) yields rendered
frames so a few hundred steps can be streamed straight into a GIF or MP4 without
ever materialising every frame in memory at once.
"""
from __future__ import annotations

from typing import Any, Callable, Iterator, List, Optional

import numpy as np
import torch

from .rule import Rule


class Universe:
    """Iterate a :class:`Rule` over time.

    Parameters
    ----------
    rule:
        The physics of this world.
    state:
        An initial state. If ``None``, ``rule.init_state()`` is used.
    seed:
        Optional global RNG seed applied before the initial state is drawn.
    """

    def __init__(
        self,
        rule: Rule,
        state: Any = None,
        *,
        seed: Optional[int] = None,
    ) -> None:
        self.rule = rule
        self.rule.eval()
        if seed is not None:
            torch.manual_seed(seed)
        self.state = rule.init_state() if state is None else state
        self.t: int = 0

    # -- evolution ---------------------------------------------------------
    @torch.no_grad()
    def step(self, n: int = 1) -> Any:
        """Advance the world ``n`` ticks in place; return the new state."""
        for _ in range(n):
            self.state = self.rule.step(self.state)
            self.t += 1
        return self.state

    @torch.no_grad()
    def frames(
        self,
        steps: int,
        *,
        every: int = 1,
        warmup: int = 0,
        scale: int = 1,
        on_frame: Optional[Callable[[int, np.ndarray], None]] = None,
    ) -> Iterator[np.ndarray]:
        """Stream rendered frames as the world evolves.

        Runs ``warmup`` silent ticks first, then advances ``steps`` ticks,
        emitting a (optionally integer-upscaled) RGB frame every ``every``
        ticks plus a final frame at the end.
        """
        if warmup:
            self.step(warmup)

        from ..render.painter import upscale  # local import avoids a cycle

        def emit(img: np.ndarray) -> np.ndarray:
            if scale != 1:
                img = upscale(img, scale)
            if on_frame is not None:
                on_frame(self.t, img)
            return img

        for i in range(steps):
            if i % every == 0:
                yield emit(self.rule.render(self.state))
            self.step()
        yield emit(self.rule.render(self.state))

    def record(self, steps: int, **kwargs: Any) -> List[np.ndarray]:
        """Eagerly collect :meth:`frames` into a list."""
        return list(self.frames(steps, **kwargs))

    # -- introspection -----------------------------------------------------
    def info(self) -> dict:
        d = {"t": self.t}
        d.update(self.rule.info(self.state))
        return d

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Universe t={self.t} rule={self.rule!r}>"
