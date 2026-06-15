"""Command-line interface: ``genre-space {seed,parse,analyze}``.

Pipeline order:  seed (optional, for a demo)  ->  parse  ->  analyze
"""

from __future__ import annotations

import argparse

from . import __version__
from .config import DEFAULT_TOP_STYLES, DEFAULT_YEAR_MAX, DEFAULT_YEAR_MIN


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="genre-space", description="Tracking how music genres are born, drift, and fade."
    )
    ap.add_argument("--version", action="version", version=f"genre-space {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p_seed = sub.add_parser("seed", help="write illustrative data.js so the visual runs now")
    p_seed.add_argument("--out", default="docs/data.js")

    p_parse = sub.add_parser("parse", help="stream a Discogs releases dump into Parquet")
    p_parse.add_argument("--input", required=True, help="discogs_*_releases.xml(.gz)")
    p_parse.add_argument("--out", default="data/releases.parquet")
    p_parse.add_argument(
        "--limit", type=int, default=None, help="stop after N releases (smoke test)"
    )
    p_parse.add_argument("--accepted-only", action="store_true", help="keep only Accepted releases")

    p_an = sub.add_parser("analyze", help="Parquet -> diversity/demography/coords -> data.js")
    p_an.add_argument("--parquet", default="data/releases.parquet")
    p_an.add_argument("--out", default="docs/data.js")
    p_an.add_argument("--top", type=int, default=DEFAULT_TOP_STYLES)
    p_an.add_argument("--year-min", type=int, default=DEFAULT_YEAR_MIN)
    p_an.add_argument("--year-max", type=int, default=DEFAULT_YEAR_MAX)

    p_fig = sub.add_parser("figures", help="render the paper's figures from data.js")
    p_fig.add_argument("--data", default="docs/data.js")
    p_fig.add_argument("--out", default="paper/figures")

    args = ap.parse_args(argv)

    if args.command == "seed":
        from .seed import make_seed

        make_seed(args.out)
    elif args.command == "parse":
        from .parse import parse_dump

        parse_dump(args.input, args.out, args.limit, args.accepted_only)
    elif args.command == "analyze":
        from .analyze import analyze

        analyze(args.parquet, args.out, args.top, args.year_min, args.year_max)
    elif args.command == "figures":
        from .figures import make_figures

        make_figures(args.data, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
