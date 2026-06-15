"""Integration tests: parse fixture, analyze, seed, figures."""

from __future__ import annotations

import duckdb

from genrespace.analyze import analyze
from genrespace.figures import make_figures
from genrespace.parse import parse_dump
from genrespace.seed import make_seed


def test_parse_explodes_rows_and_handles_missing_year(tmp_path, fixture_path):
    pq = tmp_path / "rel.parquet"
    n_rel, n_rows = parse_dump(fixture_path, pq)
    assert (n_rel, n_rows) == (9, 13)
    nulls = duckdb.sql(f"SELECT count(*) FROM '{pq}' WHERE year IS NULL").fetchone()[0]
    assert nulls == 2  # release 4 (empty) + release 9 ("198?")


def test_parse_dedups_styles_and_normalizes_unknown_country(tmp_path, fixture_path):
    pq = tmp_path / "rel.parquet"
    parse_dump(fixture_path, pq)
    n9 = duckdb.sql(f"SELECT count(*) FROM '{pq}' WHERE release_id = 9").fetchone()[0]
    assert n9 == 1  # duplicate <style>Punk</style> de-duped to one row
    c9 = duckdb.sql(f"SELECT country FROM '{pq}' WHERE release_id = 9").fetchone()[0]
    assert c9 is None  # "?" normalised to NULL


def test_parse_accepted_only_drops_deleted(tmp_path, fixture_path):
    pq = tmp_path / "rel.parquet"
    n_rel, _ = parse_dump(fixture_path, pq, accepted_only=True)
    assert n_rel == 8  # release 8 is status="Deleted"
    present = duckdb.sql(f"SELECT count(*) FROM '{pq}' WHERE release_id = 8").fetchone()[0]
    assert present == 0


def test_analyze_produces_valid_data(tmp_path, fixture_path):
    pq = tmp_path / "rel.parquet"
    parse_dump(fixture_path, pq)
    data = analyze(pq, tmp_path / "data.js", top=20)
    names = {g["name"] for g in data["genres"]}
    assert {"House", "Techno", "Boom Bap"} <= names
    house = next(g for g in data["genres"] if g["name"] == "House")
    assert house["family"] == "elec" and house["birth"] == 1985
    by_year = {r["year"]: r for r in data["diversity"]}
    assert abs(by_year[1972]["shannon"]) < 1e-6
    assert abs(by_year[1985]["shannon"] - 0.6931) < 1e-3


def test_seed_matches_schema(tmp_path, load_datajs):
    out = tmp_path / "data.js"
    make_seed(out)
    data = load_datajs(out)
    assert data["meta"]["source"] == "historical reconstruction"
    assert len(data["genres"]) > 20 and len(data["diversity"]) > 50
    g = data["genres"][0]
    assert {"name", "family", "x", "y", "birth", "peak", "counts"} <= g.keys()


def test_figures_render_and_write_numbers(tmp_path, load_datajs):
    out = tmp_path / "data.js"
    data = make_seed(out)
    paths = make_figures(data, tmp_path / "figures")
    # 4 figures × 2 formats (pdf+png) + numbers.tex = 9 files
    assert len(paths) == 9
    for p in paths:
        assert p.exists() and p.stat().st_size > 0
    numbers = (tmp_path / "numbers.tex").read_text()
    assert "\\gsShannonFirst" in numbers
    assert "\\gsTopFamLast" in numbers
