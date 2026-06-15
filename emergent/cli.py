"""``emergent`` command line — run a world, train a Neural CA, build a gallery."""
from __future__ import annotations

import argparse
import os
import time
from typing import Any, Dict, List, Optional

from . import __version__, make
from .core import describe_device, get_device
from .render import list_palettes, save_animation, save_image
from .worlds import WORLDS, list_worlds
from .worlds.neural_ca import NeuralCA, train_nca
from .worlds.targets import list_targets, make_target

_HAND_WORLDS = ["gray-scott", "lenia", "particle-life"]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _coerce(v: str) -> Any:
    low = v.lower()
    if low in {"true", "false"}:
        return low == "true"
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    if "," in v:  # simple numeric list, e.g. betas=1,0.5,0.3
        try:
            return [float(p) for p in v.split(",")]
        except ValueError:
            return v
    return v


def _overrides(args: argparse.Namespace) -> Dict[str, Any]:
    ov: Dict[str, Any] = {}
    if getattr(args, "size", None):
        ov["size"] = args.size
    if getattr(args, "palette", None) and args.world in {"gray-scott", "lenia"}:
        ov["palette"] = args.palette
    for kv in getattr(args, "set", None) or []:
        if "=" not in kv:
            raise SystemExit(f"--set expects key=value, got {kv!r}")
        k, v = kv.split("=", 1)
        ov[k] = _coerce(v)
    return ov


def _default_out(world: str, preset: Optional[str]) -> str:
    return os.path.join("gallery", f"{world}_{preset or 'default'}.gif")


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_run(args: argparse.Namespace) -> None:
    dev = get_device(args.device)
    uni = make(args.world, preset=args.preset, device=args.device, seed=args.seed, **_overrides(args))
    preset = args.preset or WORLDS[args.world].default_preset
    print(f"[emergent] {args.world} · preset={preset} · {describe_device(dev)}")
    t0 = time.time()
    frames = uni.record(args.steps, every=args.every, warmup=args.warmup, scale=args.scale)
    out = args.out or _default_out(args.world, preset)
    save_animation(frames, out, fps=args.fps)
    print(f"[emergent] wrote {out}  ({len(frames)} frames · {time.time() - t0:.1f}s)")


def cmd_nca_train(args: argparse.Namespace) -> None:
    dev = get_device(args.device)
    print(f"[emergent] training neural-ca → '{args.target}' · {describe_device(dev)}")
    iters = args.iters if args.iters is not None else (500 if args.quick else 1200)

    def log(it: int, loss: float) -> None:
        print(f"  iter {it:5d}/{iters}  loss {loss:.5f}")

    t0 = time.time()
    model, hist = train_nca(
        args.target, size=args.size, device=dev, iters=iters,
        batch=args.batch, on_log=log,
    )
    out = args.out or os.path.join("checkpoints", f"{args.target}.pt")
    model.save(out)
    print(f"[emergent] trained in {time.time() - t0:.1f}s · final loss {hist[-1]:.5f} · saved {out}")
    if args.mp4:
        _render_growth(model, args.mp4, steps=args.grow_steps, scale=args.scale,
                       damage=args.damage, fps=args.fps)


def cmd_nca_grow(args: argparse.Namespace) -> None:
    dev = get_device(args.device)
    model = NeuralCA.load(args.ckpt, device=dev)
    print(f"[emergent] growing {args.ckpt} (target={model.target_name}) · {describe_device(dev)}")
    out = args.out or os.path.join("gallery", f"neural-ca_{model.target_name}.gif")
    _render_growth(model, out, steps=args.steps, scale=args.scale, damage=args.damage, fps=args.fps)


def _render_growth(model: NeuralCA, out: str, *, steps: int, scale: int,
                   damage: bool, fps: int) -> None:
    """Grow from a single seed; optionally amputate twice and watch it heal."""
    from .core import Universe
    from .render.painter import upscale

    uni = Universe(model)
    frames: List = []
    cuts = {steps // 2, int(steps * 0.78)} if damage else set()
    total = steps + (24 if damage else 0)  # linger after the last cut
    for i in range(total):
        if i in cuts:
            side = i > steps // 2  # alternate which half we remove
            uni.state = model.damage(uni.state, where=(0.5, 0.30 if side else 0.70), radius=0.34)
        frames.append(upscale(model.render(uni.state), scale))
        uni.step()
    save_animation(frames, out, fps=fps)
    tag = " (with regeneration)" if damage else ""
    print(f"[emergent] wrote {out}  ({len(frames)} frames{tag})")


def cmd_gallery(args: argparse.Namespace) -> None:
    from .render import montage

    os.makedirs(args.out, exist_ok=True)
    dev = get_device(args.device)
    print(f"[emergent] building gallery in {args.out}/ · {describe_device(dev)}")
    heroes: List = []

    plan = [
        ("gray-scott", "coral", dict(size=200, steps=420, every=3, scale=2)),
        ("gray-scott", "fingerprint", dict(size=200, steps=420, every=3, scale=2)),
        ("lenia", "geminium", dict(size=140, steps=320, every=2, scale=3)),
        ("lenia", "orbium", dict(size=140, steps=320, every=2, scale=3)),
        ("particle-life", "ecology", dict(steps=360, every=2, scale=2)),
        ("particle-life", "cells", dict(steps=360, every=2, scale=2)),
    ]
    for world, preset, cfg in plan:
        scale = cfg.pop("scale")
        uni = make(world, preset=preset, device=args.device, seed=args.seed)
        frames = uni.record(scale=scale, **cfg)
        path = os.path.join(args.out, f"{world}_{preset}.{args.ext}")
        save_animation(frames, path, fps=args.fps)
        save_image(frames[-1], os.path.join(args.out, f"{world}_{preset}.png"))
        heroes.append(frames[-1][..., :3])
        print(f"  · {path}")

    # Neural CA, if a trained checkpoint is available.
    for target in list_targets():
        ckpt = os.path.join("checkpoints", f"{target}.pt")
        if os.path.exists(ckpt):
            model = NeuralCA.load(ckpt, device=dev)
            path = os.path.join(args.out, f"neural-ca_{target}.{args.ext}")
            _render_growth(model, path, steps=140, scale=6, damage=True, fps=args.fps)
            break

    if heroes:
        m = montage([h for h in heroes])
        save_image(m, os.path.join(args.out, "montage.png"))
        print(f"  · {os.path.join(args.out, 'montage.png')}")


def cmd_worlds(_: argparse.Namespace) -> None:
    print(f"emergent {__version__} — worlds:\n")
    for name, cls in WORLDS.items():
        presets = ", ".join(cls.presets)
        print(f"  {name:14s} {cls.description}")
        print(f"  {'':14s} presets: {presets}\n")


def cmd_palettes(_: argparse.Namespace) -> None:
    print("palettes:", ", ".join(list_palettes()))
    print("targets: ", ", ".join(list_targets()))


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def _add_run_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--preset", default=None, help="named parameter bundle")
    sp.add_argument("--steps", type=int, default=300, help="number of ticks to evolve")
    sp.add_argument("--every", type=int, default=2, help="render every Nth tick")
    sp.add_argument("--warmup", type=int, default=0, help="silent ticks before recording")
    sp.add_argument("--scale", type=int, default=2, help="integer upscale of each frame")
    sp.add_argument("--size", type=int, default=None, help="grid/canvas size override")
    sp.add_argument("--palette", default=None, help="palette (gray-scott/lenia)")
    sp.add_argument("--fps", type=int, default=30)
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--device", default="auto", help="auto|cpu|cuda|mps")
    sp.add_argument("--out", default=None, help="output .gif/.mp4/.png path")
    sp.add_argument("--set", action="append", metavar="KEY=VAL",
                    help="override any rule parameter (repeatable)")
    sp.set_defaults(func=cmd_run)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="emergent", description=__doc__)
    p.add_argument("--version", action="version", version=f"emergent {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    for world in _HAND_WORLDS:
        sp = sub.add_parser(world, help=WORLDS[world].description)
        sp.set_defaults(world=world)
        _add_run_args(sp)

    nca = sub.add_parser("neural-ca", help=WORLDS["neural-ca"].description)
    nsub = nca.add_subparsers(dest="action", required=True)

    tr = nsub.add_parser("train", help="learn a rule that grows a target")
    tr.add_argument("--target", default="heart", choices=list_targets())
    tr.add_argument("--size", type=int, default=40)
    tr.add_argument("--iters", type=int, default=None)
    tr.add_argument("--batch", type=int, default=8)
    tr.add_argument("--quick", action="store_true", help="fewer iterations")
    tr.add_argument("--out", default=None, help="checkpoint .pt path")
    tr.add_argument("--mp4", default=None, help="also render a growth clip here")
    tr.add_argument("--grow-steps", type=int, default=140)
    tr.add_argument("--scale", type=int, default=6)
    tr.add_argument("--damage", action="store_true", help="include a regeneration clip")
    tr.add_argument("--fps", type=int, default=20)
    tr.add_argument("--device", default="auto")
    tr.set_defaults(func=cmd_nca_train)

    gr = nsub.add_parser("grow", help="grow (and optionally heal) from a checkpoint")
    gr.add_argument("--ckpt", required=True)
    gr.add_argument("--steps", type=int, default=140)
    gr.add_argument("--scale", type=int, default=6)
    gr.add_argument("--damage", action="store_true")
    gr.add_argument("--fps", type=int, default=20)
    gr.add_argument("--device", default="auto")
    gr.add_argument("--out", default=None)
    gr.set_defaults(func=cmd_nca_grow)

    g = sub.add_parser("gallery", help="render a curated gallery of every world")
    g.add_argument("--out", default="gallery")
    g.add_argument("--ext", default="gif", choices=["gif", "mp4"])
    g.add_argument("--fps", type=int, default=30)
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--device", default="auto")
    g.set_defaults(func=cmd_gallery)

    sub.add_parser("worlds", help="list worlds and presets").set_defaults(func=cmd_worlds)
    sub.add_parser("palettes", help="list palettes and targets").set_defaults(func=cmd_palettes)
    return p


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
