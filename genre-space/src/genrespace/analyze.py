"""Turn ``releases.parquet`` into the JSON the visual reads (``docs/data.js``).

Computes, per the project's scope:

* per-style release counts by year      — bubble size + streamgraph
* Shannon & Simpson diversity per year   — the paper's headline series
* demography per style (birth / peak)    — when bubbles bloom
* 2-D coordinates from style co-occurrence — a data-derived genre-space layout

Writes ``window.GENRE_DATA = {...}`` as a ``<script src>`` include, so the visual
stays a shareable single page with no fetch/CORS hassle.
"""

from __future__ import annotations

import datetime as dt
import json
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa

from .config import (
    DEFAULT_TOP_STYLES,
    DEFAULT_YEAR_MAX,
    DEFAULT_YEAR_MIN,
    FAMILIES,
    FAMILY_OF,
)
from .definitions import DEFINITIONS


def coords_from_cooccurrence(con, styles: list[str], ymin: int, ymax: int) -> np.ndarray:
    """MDS layout of styles from how often they're tagged on the same release.

    Expects a registered DuckDB relation ``top(style)`` of the styles of interest.
    Falls back to a ring layout when there isn't enough signal (e.g. a tiny fixture).
    """
    idx = {s: i for i, s in enumerate(styles)}
    n = len(styles)
    matrix = np.zeros((n, n))
    rows = con.execute(
        f"""
        SELECT a.style s1, b.style s2, COUNT(*) c
        FROM t a JOIN t b USING (release_id)
        WHERE a.style < b.style
              AND a.style IN (SELECT style FROM top)
              AND b.style IN (SELECT style FROM top)
              AND a.year BETWEEN {int(ymin)} AND {int(ymax)}
        GROUP BY 1, 2
        """
    ).fetchall()
    for s1, s2, c in rows:
        i, j = idx[s1], idx[s2]
        matrix[i, j] = matrix[j, i] = c

    if n < 4 or matrix.sum() == 0:
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.c_[50 + 38 * np.cos(ang), 50 + 38 * np.sin(ang)]

    norm = np.sqrt(np.outer(matrix.diagonal() + matrix.sum(1), matrix.diagonal() + matrix.sum(1)))
    sim = matrix / np.where(norm == 0, 1, norm)
    dist = 1 - sim
    np.fill_diagonal(dist, 0)

    from sklearn.manifold import MDS

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        xy = MDS(
            n_components=2,
            dissimilarity="precomputed",
            random_state=7,
            n_init=1,
            normalized_stress="auto",
        ).fit_transform(dist)

    for k in (0, 1):  # scale into a 5..95 box
        lo, hi = xy[:, k].min(), xy[:, k].max()
        xy[:, k] = 5 + 90 * (xy[:, k] - lo) / (hi - lo if hi > lo else 1)
    return xy


def analyze(
    parquet: str | Path,
    out: str | Path,
    top: int = DEFAULT_TOP_STYLES,
    ymin: int = DEFAULT_YEAR_MIN,
    ymax: int = DEFAULT_YEAR_MAX,
) -> dict:
    """Read ``parquet`` and write ``out`` (``data.js``). Returns the data dict."""
    con = duckdb.connect()
    pq_path = str(parquet).replace("'", "''")
    con.execute(
        f"CREATE VIEW t AS SELECT * FROM read_parquet('{pq_path}') "
        f"WHERE year BETWEEN {int(ymin)} AND {int(ymax)}"
    )

    # ---- pick the top styles by total volume ----
    top_styles = [
        r[0]
        for r in con.execute(
            "SELECT style, COUNT(*) c FROM t WHERE style IS NOT NULL "
            "GROUP BY 1 ORDER BY c DESC LIMIT ?",
            [top],
        ).fetchall()
    ]
    con.register("top", pa.table({"style": top_styles}))  # for IN-subqueries

    # ---- per (style, year) counts + the style's modal family ----
    rows = con.execute(
        "SELECT style, year, COUNT(*) c FROM t WHERE style IN (SELECT style FROM top) GROUP BY 1, 2"
    ).fetchall()
    counts: dict[str, dict[int, int]] = {}
    for s, y, c in rows:
        counts.setdefault(s, {})[int(y)] = int(c)

    fam_rows = con.execute(
        """
        SELECT style, genre, COUNT(*) c FROM t
        WHERE style IN (SELECT style FROM top) AND genre IS NOT NULL GROUP BY 1, 2
        QUALIFY ROW_NUMBER() OVER (PARTITION BY style ORDER BY c DESC) = 1
        """
    ).fetchall()
    fam_of_style = {s: FAMILY_OF.get(g, "other") for s, g, _ in fam_rows}

    xy = coords_from_cooccurrence(con, top_styles, ymin, ymax)

    genres = []
    for i, s in enumerate(top_styles):
        ct = counts.get(s, {})
        if not ct:
            continue
        peak = max(ct, key=ct.get)
        thr = max(3, 0.04 * ct[peak])  # birth = first year reaching a fraction of peak
        birth = min((y for y, c in ct.items() if c >= thr), default=min(ct))
        genres.append(
            {
                "name": s,
                "family": fam_of_style.get(s, "other"),
                "x": round(float(xy[i, 0]), 1),
                "y": round(float(xy[i, 1]), 1),
                "birth": int(birth),
                "peak": int(peak),
                "def": DEFINITIONS.get(s, ""),
                "counts": {str(y): c for y, c in sorted(ct.items())},
            }
        )

    # ---- diversity per year over ALL styles (not just the top) ----
    div_rows = con.execute(
        """
        WITH yc AS (
          SELECT year, style, COUNT(*) c FROM t WHERE style IS NOT NULL GROUP BY 1, 2),
        yt AS (SELECT year, SUM(c) tot, COUNT(*) nstyles FROM yc GROUP BY year),
        p  AS (SELECT yc.year, c * 1.0 / yt.tot AS p FROM yc JOIN yt USING (year))
        SELECT yt.year, yt.tot, yt.nstyles,
               -SUM(p.p * LN(p.p)) AS shannon,
               1 - SUM(p.p * p.p)  AS simpson
        FROM p JOIN yt USING (year)
        GROUP BY yt.year, yt.tot, yt.nstyles ORDER BY yt.year
        """
    ).fetchall()
    diversity = [
        {
            "year": int(y),
            "releases": int(tot),
            "nStyles": int(nst),
            "shannon": round(sh, 4),
            "simpson": round(si, 4),
        }
        for (y, tot, nst, sh, si) in div_rows
    ]

    data = {
        "meta": {
            "source": "discogs",
            "generated": dt.date.today().isoformat(),
            "yearMin": ymin,
            "yearMax": ymax,
            "note": "release counts from a Discogs data dump (Public Domain)",
        },
        "families": FAMILIES,
        "genres": genres,
        "diversity": diversity,
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.GENRE_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print(f"wrote {out}  ({len(genres)} styles, {len(diversity)} years)")
    return data
