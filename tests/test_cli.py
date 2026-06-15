import pytest

from emergent.cli import _coerce, build_parser


def test_coerce_types():
    assert _coerce("3") == 3 and isinstance(_coerce("3"), int)
    assert _coerce("3.5") == 3.5
    assert _coerce("true") is True and _coerce("False") is False
    assert _coerce("1,0.5,0.3") == [1.0, 0.5, 0.3]
    assert _coerce("ember") == "ember"


def test_parser_world_run():
    p = build_parser()
    args = p.parse_args(["lenia", "--preset", "geminium", "--steps", "12", "--scale", "3"])
    assert args.world == "lenia" and args.preset == "geminium"
    assert args.steps == 12 and args.scale == 3 and args.func.__name__ == "cmd_run"


def test_parser_neural_ca_subactions():
    p = build_parser()
    tr = p.parse_args(["neural-ca", "train", "--target", "star", "--quick"])
    assert tr.action == "train" and tr.target == "star" and tr.quick is True
    gr = p.parse_args(["neural-ca", "grow", "--ckpt", "x.pt", "--damage"])
    assert gr.action == "grow" and gr.ckpt == "x.pt" and gr.damage is True


def test_parser_requires_subcommand():
    p = build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_run_smoke_writes_file(tmp_path):
    # End-to-end: parse args and actually render a tiny clip.
    from emergent.cli import main

    out = tmp_path / "tiny.gif"
    main(["gray-scott", "--size", "16", "--steps", "6", "--every", "2",
          "--scale", "1", "--out", str(out), "--set", "substeps=1"])
    assert out.exists() and out.stat().st_size > 0
