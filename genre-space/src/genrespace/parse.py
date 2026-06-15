"""Stream a Discogs *releases* data dump into a tidy Parquet file.

The Discogs monthly dumps are large (the releases XML is tens of GB uncompressed),
so we stream with ``lxml.iterparse`` and clear elements as we go — memory stays flat.

Output schema (one row per release-style; the release's primary genre rides along)::

    release_id : int64
    year       : int32   (nullable)
    country    : string
    genre      : string  (nullable)
    style      : string  (nullable)

Dumps (Public Domain): https://discogs-data-dumps.s3.us-west-2.amazonaws.com/
"""

from __future__ import annotations

import gzip
import re
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree

YEAR_RE = re.compile(r"(\d{4})")
SCHEMA = pa.schema(
    [
        ("release_id", pa.int64()),
        ("year", pa.int32()),
        ("country", pa.string()),
        ("genre", pa.string()),
        ("style", pa.string()),
    ]
)


def _open(path: str | Path):
    return gzip.open(path, "rb") if str(path).endswith(".gz") else open(path, "rb")


def _year(text: str | None) -> int | None:
    if not text:
        return None
    m = YEAR_RE.search(text)
    if not m:
        return None
    y = int(m.group(1))
    return y if 1900 <= y <= 2100 else None


def _clean(items):
    """Strip, drop blanks, de-duplicate while preserving first-seen order."""
    return list(dict.fromkeys(s.strip() for s in items if s and s.strip()))


def iter_releases(fh):
    """Yield ``(release_id, year, country, [genres], [styles], status)`` per ``<release>``."""
    context = etree.iterparse(fh, events=("end",), tag="release", recover=True)
    for _, rel in context:
        rid = rel.get("id")
        rid = int(rid) if rid and rid.isdigit() else None
        status = rel.get("status")  # Accepted / Draft / Deleted / Rejected
        year = _year(rel.findtext("released"))
        country = (rel.findtext("country") or "").strip()
        country = country if country and country != "?" else None  # Discogs uses "?" for unknown
        genres = _clean(g.text for g in rel.findall("genres/genre"))
        styles = _clean(s.text for s in rel.findall("styles/style"))
        yield rid, year, country, genres, styles, status
        # free memory: clear this element and any earlier siblings
        rel.clear()
        while rel.getprevious() is not None:
            del rel.getparent()[0]


def parse_dump(
    input_path: str | Path,
    out_path: str | Path,
    limit: int | None = None,
    accepted_only: bool = False,
    batch_rows: int = 500_000,
) -> tuple[int, int]:
    """Parse ``input_path`` (``.xml`` or ``.xml.gz``) into ``out_path`` Parquet.

    With ``accepted_only=True``, skip releases whose Discogs status isn't ``Accepted``
    (the usual data-quality filter). Returns ``(n_releases, n_rows)``.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(out_path, SCHEMA, compression="zstd")

    cols: dict[str, list] = {k: [] for k in ("release_id", "year", "country", "genre", "style")}
    n_rel = n_rows = 0
    t0 = time.time()

    def flush() -> None:
        nonlocal cols
        if not cols["release_id"]:
            return
        writer.write_table(pa.table(cols, schema=SCHEMA))
        cols = {k: [] for k in cols}

    try:
        with _open(input_path) as fh:
            for rid, year, country, genres, styles, status in iter_releases(fh):
                if accepted_only and status not in (None, "Accepted"):
                    continue
                n_rel += 1
                primary = genres[0] if genres else None
                pairs = [(primary, s) for s in styles] or [(g, None) for g in genres] or []
                for g, s in pairs:
                    cols["release_id"].append(rid)
                    cols["year"].append(year)
                    cols["country"].append(country)
                    cols["genre"].append(g)
                    cols["style"].append(s)
                    n_rows += 1
                if n_rows and n_rows % batch_rows < len(pairs):
                    flush()
                if n_rel % 200_000 == 0:
                    rate = n_rel / (time.time() - t0)
                    print(
                        f"  ...{n_rel:,} releases / {n_rows:,} rows  ({rate:,.0f} rel/s)",
                        file=sys.stderr,
                    )
                if limit and n_rel >= limit:
                    break
        flush()
    finally:
        writer.close()

    print(
        f"parsed {n_rel:,} releases -> {n_rows:,} rows -> {out_path}  ({time.time() - t0:.1f}s)",
        file=sys.stderr,
    )
    return n_rel, n_rows
