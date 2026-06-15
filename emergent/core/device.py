"""Device selection — keep every world device-agnostic.

Worlds are written against an abstract ``torch.device`` so the exact same code
runs on CPU here and lights up a GPU the moment one is available.
"""
from __future__ import annotations

import torch


def _mps_available() -> bool:
    backend = getattr(torch.backends, "mps", None)
    return bool(backend is not None and backend.is_available())


def get_device(prefer: str = "auto") -> torch.device:
    """Return a sensible :class:`torch.device`.

    Parameters
    ----------
    prefer:
        ``"auto"`` picks CUDA, then Apple MPS, then CPU. Pass ``"cpu"``,
        ``"cuda"`` or ``"mps"`` to force a specific backend (falling back to
        CPU if the requested backend is unavailable).
    """
    prefer = (prefer or "auto").lower()
    if prefer not in {"auto", "cpu", "cuda", "mps"}:
        raise ValueError(f"unknown device preference: {prefer!r}")

    if prefer == "cpu":
        return torch.device("cpu")
    if prefer == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if prefer == "mps":
        return torch.device("mps" if _mps_available() else "cpu")

    # auto
    if torch.cuda.is_available():
        return torch.device("cuda")
    if _mps_available():
        return torch.device("mps")
    return torch.device("cpu")


def describe_device(device: torch.device) -> str:
    """Human-readable one-liner about a device, for logs and CLIs."""
    device = torch.device(device)
    if device.type == "cuda":
        idx = device.index or 0
        name = torch.cuda.get_device_name(idx)
        return f"cuda:{idx} ({name})"
    if device.type == "mps":
        return "mps (Apple Metal)"
    return f"cpu ({torch.get_num_threads()} threads)"
