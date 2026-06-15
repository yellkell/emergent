"""Train the Neural CA on a few targets and render growth + regeneration clips.

Run from the repo root::

    python scripts/train_gallery_nca.py

Produces ``checkpoints/<target>.pt`` and ``gallery/neural-ca_<target>.{gif,mp4}``.
"""
from __future__ import annotations

import os
import sys
import time

# Make the repo importable when run as a loose script (python scripts/...).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from emergent.worlds.neural_ca import train_nca

# (target, training iterations, RNG seed). Bold shapes grow crisply on a CPU
# budget; over-detailed targets (e.g. ladybug spots) need far more iterations.
JOBS = [
    ("heart", 2500, 0),
    ("star", 2500, 2),
    ("flower", 2200, 3),
]


def main() -> None:
    for name, iters, seed in JOBS:
        torch.manual_seed(seed)
        print(f"\n=== training neural-ca → {name} ({iters} iters) ===", flush=True)
        t0 = time.time()
        model, hist = train_nca(
            name, size=40, iters=iters,
            on_log=lambda it, l, n=name: print(f"  [{n}] iter {it:5d}  loss {l:.5f}", flush=True),
        )
        model.save(f"checkpoints/{name}.pt")
        print(f"  [{name}] trained in {time.time() - t0:.0f}s  final loss {hist[-1]:.5f}", flush=True)
    print("\n=== neural-ca training complete ===", flush=True)


if __name__ == "__main__":
    main()
