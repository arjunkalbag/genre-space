#!/usr/bin/env python3
"""Download the latest Discogs *releases* dump (Public Domain) into ``data/``.

Run this on your own machine: ``python scripts/fetch_discogs.py``.

NOTE: this talks to Discogs' S3 bucket, which the project's CI/sandbox can't reach, so
it isn't covered by the test suite — it's a convenience wrapper around the documented
download. If it ever drifts, just grab the file by hand from the bucket index below.

    bucket: https://discogs-data-dumps.s3.us-west-2.amazonaws.com/
    files : data/<year>/discogs_<YYYYMMDD>_releases.xml.gz
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BUCKET = "https://discogs-data-dumps.s3.us-west-2.amazonaws.com"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def latest_key(kind: str, year: int) -> str | None:
    """Return the newest ``data/<year>/discogs_*_<kind>.xml.gz`` key, or None."""
    url = f"{BUCKET}/?list-type=2&prefix=data/{year}/"
    with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (trusted host)
        root = ET.fromstring(r.read())
    keys = [c.findtext(f"{NS}Key") for c in root.findall(f"{NS}Contents")]
    matches = sorted(k for k in keys if k and k.endswith(f"_{kind}.xml.gz"))
    return matches[-1] if matches else None


def _progress(done: int, total: int) -> None:
    if total > 0:
        pct = done / total * 100
        sys.stderr.write(f"\r  {done / 1e9:5.2f} / {total / 1e9:5.2f} GB ({pct:4.1f}%)")
        sys.stderr.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description="Download the latest Discogs dump.")
    ap.add_argument(
        "--kind", default="releases", choices=["releases", "artists", "labels", "masters"]
    )
    ap.add_argument("--year", type=int, default=dt.date.today().year)
    ap.add_argument("--out-dir", default="data")
    args = ap.parse_args()

    key = latest_key(args.kind, args.year) or latest_key(args.kind, args.year - 1)
    if not key:
        sys.exit(
            f"no {args.kind} dump found for {args.year} or {args.year - 1}; "
            f"browse {BUCKET}/ and download manually."
        )

    out = Path(args.out_dir) / Path(key).name
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {key}\n  -> {out}", file=sys.stderr)

    with urllib.request.urlopen(f"{BUCKET}/{key}", timeout=60) as r:  # noqa: S310
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        with open(out, "wb") as fh:
            while chunk := r.read(1 << 20):
                fh.write(chunk)
                done += len(chunk)
                _progress(done, total)
    sys.stderr.write("\n")
    print(f"done. next: genre-space parse --input {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
