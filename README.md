# genre-space

An interactive, zoomable map of music genre evolution (1950–2024) paired with a research paper. By Arjun Kalbag.

**Live site:** https://genre-space.netlify.app/

---

## Files

| File | What it is |
|---|---|
| `genre-space.html` | Self-contained interactive |
| `genre-space-paper.pdf` | Research paper: *The Genre Explosion: Diversity, Demography, and the Shape of Recorded Music, 1950–2024* |

---

## Tech stack

### Interactive (`genre-space.html`)
- **Vanilla JS + SVG** — no frameworks, no build step
- Spring-physics animation for the bubbles (damped harmonic oscillator)
- Pointer-events zoom/pan/pinch via a single SVG viewport transform
- Two views: **Map** (2D co-occurrence layout, animated over time) and **Stream** (normalised family share)
- Data inlined as `window.GENRE_DATA` — 229 documented genre styles, each with a one-line definition
- Fonts via Google Fonts CDN (Bricolage Grotesque, DM Mono)

### Paper (`genre-space-paper.pdf`)
- Written in **LaTeX** (`article` class, 12pt, A4)
- Figures generated with **matplotlib** (vector PDF, 300-DPI PNG fallback)
- 2D genre layout from **scikit-learn MDS** on a style co-occurrence matrix
- Bibliography via **BibTeX** / `natbib`
- Compiled with `pdflatex` ×3 + `bibtex`

### Data pipeline (optional — for swapping in real Discogs counts)
- **Python 3.10+** package (`src/genrespace/`)
- Parses Discogs monthly XML dumps (Public Domain) with `lxml` streaming + `pyarrow` → Parquet
- Queries with **DuckDB** (Shannon/Simpson diversity, genre demography, co-occurrence MDS)
- CLI: `genre-space seed | parse | analyze | figures`
- Tests with `pytest`; linting with `ruff`

---

## Data

229 genre styles drawn from the Discogs controlled vocabulary. Birth years are sourced from Bogdanov & Serra (2017), Grove Music Online, and documented music history. Catalogue-volume curves are calibrated to match the aggregate statistics in Bogdanov & Serra (2017) and the diversity trajectory in Mauch et al. (2015). Each style also carries a concise definition.

---

## References

- Mauch et al. (2015). *The Evolution of Popular Music: USA 1960–2010.* Royal Society Open Science. [arXiv:1502.05417](https://arxiv.org/abs/1502.05417)
- Bogdanov & Serra (2017). *Quantifying Music Trends and Facts Using Editorial Metadata from the Discogs Database.* ISMIR.
- Serrà et al. (2012). *Measuring the Evolution of Contemporary Western Popular Music.* Scientific Reports.

---

MIT License
