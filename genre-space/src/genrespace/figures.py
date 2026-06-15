"""Generate publication-quality figures and a LaTeX numbers file from analyzed data.

Figures (saved as PDF + 300-DPI PNG for the paper):
  1. diversity.pdf    — Shannon entropy & Gini-Simpson diversity over time
  2. genre_share.pdf  — normalised stacked-area by colour family
  3. demography.pdf   — new styles born per 5-year period
  4. genre_map.pdf    — 2-D genre-space map at the final year

Also writes ``paper/numbers.tex`` — LaTeX ``\newcommand`` macros so specific
numbers in the paper auto-update when the pipeline is re-run.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from .config import FAMILIES

# ---------------------------------------------------------------------------
# Typography + style  (fits a single-column 15 cm text-width paper)
# ---------------------------------------------------------------------------
FIG_W = 5.9  # inches  ≈ 15 cm
FIG_H = 3.4
FIG_H_TALL = 4.0

RC = {
    "figure.figsize": (FIG_W, FIG_H),
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    # typography
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 8.5,
    "axes.titlesize": 9.5,
    "axes.titleweight": "semibold",
    "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "legend.frameon": False,
    # spines / grid
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#BBBBBB",
    "axes.linewidth": 0.7,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#EEEEEE",
    "grid.linewidth": 0.6,
    # ticks
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.color": "#555555",
    "ytick.color": "#555555",
    "text.color": "#1B1B22",
    "axes.labelcolor": "#444444",
}

CORAL = "#FF6F61"
TEAL = "#45C4E0"
PURPLE = "#9B7BE8"
GREY = "#9A9AA6"


def _load(data) -> dict:
    if isinstance(data, dict):
        return data
    text = Path(data).read_text().strip()
    return json.loads(re.sub(r"^window\.GENRE_DATA = |;$", "", text))


def _save(fig, path_stem: Path) -> tuple[Path, Path]:
    pdf = path_stem.with_suffix(".pdf")
    png = path_stem.with_suffix(".png")
    fig.savefig(pdf)
    fig.savefig(png)
    plt.close(fig)
    return pdf, png


# ---------------------------------------------------------------------------
# Figure 1: Diversity
# ---------------------------------------------------------------------------
def _fig_diversity(div: list[dict], outdir: Path) -> tuple[Path, Path]:
    years = [r["year"] for r in div]
    shan = [r["shannon"] for r in div]
    simp = [r["simpson"] for r in div]

    with plt.rc_context(RC):
        fig, ax1 = plt.subplots()
        ax1.plot(years, shan, color=CORAL, lw=2.0, label="Shannon $H$")
        ax1.set_xlabel("year")
        ax1.set_ylabel("Shannon entropy $H$", color=CORAL)
        ax1.tick_params(axis="y", labelcolor=CORAL)
        ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))

        ax2 = ax1.twinx()
        ax2.plot(
            years,
            simp,
            color=TEAL,
            lw=1.6,
            linestyle="--",
            label="Gini\u2013Simpson $1-\\lambda$",
        )
        ax2.set_ylabel("Gini\u2013Simpson $1\\!-\\!\\lambda$", color=TEAL)
        ax2.tick_params(axis="y", labelcolor=TEAL)
        ax2.set_ylim(0, 1.05)
        ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
        ax2.grid(False)
        ax2.spines["top"].set_visible(False)

        # combined legend
        lines = ax1.get_lines() + ax2.get_lines()
        ax1.legend(lines, [ln.get_label() for ln in lines], loc="upper left", ncol=2)
        ax1.set_title("Diversity of the genre-space, 1950–2024")
        fig.tight_layout()
        return _save(fig, outdir / "diversity")


# ---------------------------------------------------------------------------
# Figure 2: Genre family share
# ---------------------------------------------------------------------------
def _fig_genre_share(
    genres: list[dict], div: list[dict], fams: dict, outdir: Path
) -> tuple[Path, Path]:
    ymin = min(r["year"] for r in div)
    ymax = max(r["year"] for r in div)
    yrs = list(range(ymin, ymax + 1))

    # sort families by total volume (largest first for nicer stacking)
    fam_keys = sorted(
        {g["family"] for g in genres},
        key=lambda f: -sum(sum(g["counts"].values()) for g in genres if g["family"] == f),
    )

    totals = dict.fromkeys(yrs, 0)
    per_fam = {f: dict.fromkeys(yrs, 0) for f in fam_keys}
    for g in genres:
        for ys, c in g["counts"].items():
            y = int(ys)
            if ymin <= y <= ymax:
                per_fam[g["family"]][y] += c
                totals[y] += c

    shares = [
        [(per_fam[f][y] / totals[y] * 100 if totals[y] else 0) for y in yrs] for f in fam_keys
    ]

    with plt.rc_context({**RC, "figure.figsize": (FIG_W, FIG_H_TALL)}):
        fig, ax = plt.subplots()
        ax.stackplot(
            yrs,
            shares,
            colors=[(fams.get(f) or FAMILIES.get(f) or {}).get("color", GREY) for f in fam_keys],
            labels=[(fams.get(f) or FAMILIES.get(f) or {}).get("label", f) for f in fam_keys],
            alpha=0.88,
        )
        ax.set_xlim(ymin, ymax)
        ax.set_ylim(0, 100)
        ax.set_ylabel("share of releases (%)")
        ax.set_xlabel("year")
        ax.set_title("Genre family share, 1950–2024")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0))
        ax.legend(loc="upper left", ncol=2, fontsize=7)
        fig.tight_layout()
        return _save(fig, outdir / "genre_share")


# ---------------------------------------------------------------------------
# Figure 3: Demography (new styles born per decade)
# ---------------------------------------------------------------------------
def _fig_demography(genres: list[dict], outdir: Path) -> tuple[Path, Path]:
    bins = Counter((g["birth"] // 10) * 10 for g in genres)
    xs = sorted(bins)
    counts = [bins[b] for b in xs]
    labels = [f"{b}s" for b in xs]

    # colour bars by era (cool → warm gradient)
    n = len(xs)
    cmap = mpl.colormaps["plasma"]
    colors = [cmap(0.15 + 0.7 * i / max(n - 1, 1)) for i in range(n)]

    with plt.rc_context(RC):
        fig, ax = plt.subplots()
        bars = ax.bar(labels, counts, color=colors, width=0.72, linewidth=0)
        ax.set_ylabel("new styles born")
        ax.set_xlabel("decade")
        ax.set_title("Rate of new style emergence, 1950–2024")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        # value labels on bars
        for bar, val in zip(bars, counts, strict=False):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(val),
                    ha="center",
                    va="bottom",
                    fontsize=6.5,
                )
        fig.tight_layout()
        return _save(fig, outdir / "demography")


# ---------------------------------------------------------------------------
# Figure 4: Genre map snapshot (final year)
# ---------------------------------------------------------------------------
def _fig_genre_map(genres: list[dict], fams: dict, ymax: int, outdir: Path) -> tuple[Path, Path]:
    # Use release volume at ymax as bubble size
    sizes, xs, ys, colors, names = [], [], [], [], []
    for g in genres:
        vol = g["counts"].get(str(ymax), 0)
        if vol == 0:
            continue
        col = (fams.get(g["family"]) or FAMILIES.get(g["family"]) or {}).get("color", GREY)
        xs.append(g["x"])
        ys.append(g["y"])
        sizes.append(vol)
        colors.append(col)
        names.append(g["name"])

    max_s = max(sizes) if sizes else 1
    radii = [5 + 950 * (s / max_s) ** 0.55 for s in sizes]

    with plt.rc_context({**RC, "figure.figsize": (FIG_W, FIG_W * 0.85), "axes.grid": False}):
        fig, ax = plt.subplots()
        ax.scatter(xs, ys, s=radii, c=colors, alpha=0.65, linewidths=0.5, edgecolors="white")

        # Label only the most prominent styles, and greedily drop any label
        # that would collide with one already placed, to keep the map readable.
        order = sorted(range(len(names)), key=lambda i: -sizes[i])
        threshold = np.percentile(sizes, 80) if sizes else 0
        placed: list[tuple[float, float]] = []
        MIN_DX, MIN_DY = 7.0, 4.2  # data-unit spacing below which labels collide
        for i in order:
            x, y, name, vol = xs[i], ys[i], names[i], sizes[i]
            if vol < threshold:
                continue
            if any(abs(x - px) < MIN_DX and abs(y - py) < MIN_DY for px, py in placed):
                continue
            placed.append((x, y))
            ax.annotate(
                name,
                (x, y),
                fontsize=5.6,
                ha="center",
                va="bottom",
                xytext=(0, 4),
                textcoords="offset points",
                color="#222222",
            )

        # family legend (one proxy circle per family present)
        seen_fams = sorted({g["family"] for g in genres if g["counts"].get(str(ymax), 0) > 0})
        handles = [
            plt.scatter(
                [],
                [],
                s=60,
                color=(fams.get(f) or FAMILIES.get(f) or {}).get("color", GREY),
                alpha=0.8,
                label=(fams.get(f) or FAMILIES.get(f) or {}).get("label", f),
            )
            for f in seen_fams
        ]
        ax.legend(
            handles=handles,
            loc="lower right",
            ncol=2,
            fontsize=6.5,
            frameon=True,
            framealpha=0.9,
            edgecolor="#DDDDDD",
        )

        ax.set_xlabel("← acoustic / organic   ·   electronic / synthetic →", fontsize=7, color=GREY)
        ax.set_ylabel("← spiky / percussive   ·   atmospheric / dense →", fontsize=7, color=GREY)
        ax.set_title(
            f"Genre-space map, {ymax}\n"
            f"(bubble size ≈ catalogue volume; axes are an editorial placement)",
            fontsize=8.5,
        )
        ax.set_xlim(-3, 103)
        ax.set_ylim(-3, 103)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        for sp in ax.spines.values():
            sp.set_visible(False)
        fig.tight_layout()
        return _save(fig, outdir / "genre_map")


# ---------------------------------------------------------------------------
# numbers.tex
# ---------------------------------------------------------------------------
def _write_numbers(data: dict, outdir: Path) -> Path:
    div = data["diversity"]
    genres = data["genres"]
    ymin = data["meta"]["yearMin"]
    ymax = data["meta"]["yearMax"]
    source = data["meta"]["source"]

    first = next((r for r in div if r["year"] == ymin), div[0])
    last = next((r for r in div if r["year"] == ymax), div[-1])
    peak_div_year = max(div, key=lambda r: r["shannon"])["year"]

    bins = Counter((g["birth"] // 10) * 10 for g in genres)
    by_decade = sorted(bins.items(), key=lambda kv: -kv[1])
    peak_birth_period = by_decade[0][0]
    peak_birth_count = by_decade[0][1]
    # decade immediately preceding the peak, for the comparison sentence
    prev_decade = peak_birth_period - 10
    prev_decade_count = bins.get(prev_decade, 0)

    # family shares at ymin and ymax
    def fam_share(year):
        tot = sum(g["counts"].get(str(year), 0) for g in genres)
        if tot == 0:
            return {}
        return {
            f: round(
                sum(g["counts"].get(str(year), 0) for g in genres if g["family"] == f) / tot * 100,
                1,
            )
            for f in {g["family"] for g in genres}
        }

    share_first = fam_share(ymin)
    share_last = fam_share(ymax)

    top_fam_last = max(share_last, key=share_last.get) if share_last else "rock"
    top_fam_first = max(share_first, key=share_first.get) if share_first else "roots"

    growth = last["shannon"] / first["shannon"] if first["shannon"] > 0 else 0

    cmds = {
        "DataSource": source,
        "YearMin": str(ymin),
        "YearMax": str(ymax),
        "NStyles": str(len(genres)),
        "ShannonFirst": f"{first['shannon']:.2f}",
        "ShannonLast": f"{last['shannon']:.2f}",
        "ShannonGrowth": f"{growth:.1f}",
        "SimpsonFirst": f"{first['simpson']:.2f}",
        "SimpsonLast": f"{last['simpson']:.2f}",
        "NStylesFirstYear": str(first["nStyles"]),
        "NStylesLastYear": str(last["nStyles"]),
        "PeakDivYear": str(peak_div_year),
        "PeakBirthPeriod": f"{peak_birth_period}s",
        "PeakBirthCount": str(peak_birth_count),
        "PrevDecade": f"{prev_decade}s",
        "PrevDecadeCount": str(prev_decade_count),
        "TopFamFirst": (FAMILIES.get(top_fam_first) or {}).get("label", top_fam_first),
        "TopFamLast": (FAMILIES.get(top_fam_last) or {}).get("label", top_fam_last),
        "TopFamLastShare": f"{share_last.get(top_fam_last, 0):.0f}",
    }

    out = outdir.parent / "numbers.tex"
    lines = [
        "% AUTO-GENERATED by genre-space figures — do not edit by hand.",
        "% Re-run `genre-space figures` to refresh after a new pipeline run.",
        "",
    ]
    for k, v in cmds.items():
        lines.append(f"\\newcommand{{\\gs{k}}}{{{v}}}")
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def make_figures(data, outdir: str | Path = "paper/figures") -> list[Path]:
    """Render figures into ``outdir`` and write ``paper/numbers.tex``.
    Returns list of written paths (PDFs + PNGs + numbers.tex).
    """
    d = _load(data)
    fams = d["families"]
    genres = d["genres"]
    div = d["diversity"]
    ymax = d["meta"]["yearMax"]

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for pair in [
        _fig_diversity(div, outdir),
        _fig_genre_share(genres, div, fams, outdir),
        _fig_demography(genres, outdir),
        _fig_genre_map(genres, fams, ymax, outdir),
    ]:
        written.extend(pair)

    written.append(_write_numbers(d, outdir))
    print(f"wrote {len(written)} files -> {outdir}")
    return written
