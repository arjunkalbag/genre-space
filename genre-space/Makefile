.DEFAULT_GOAL := help
.PHONY: help setup seed run paper serve deploy test lint fmt clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## install the package and dev tools
	pip install -e ".[dev]"

seed: ## write illustrative data so the site runs immediately
	python -m genrespace seed

run: seed ## seed data + open the site
	python -m http.server -d docs 8000

paper: ## compile paper/paper.pdf  (requires TeX Live)
	python -m genrespace figures
	cd paper && make
	cp paper/paper.pdf docs/paper.pdf

serve: ## serve the site at http://localhost:8000
	python -m http.server -d docs 8000

deploy: ## push to GitHub (site goes live at arjunkalbag.github.io/genre-space)
	git add docs/ paper/paper.pdf
	git commit -m "Update site and paper"
	git push

# ---- full pipeline (once you have the Discogs dump) ----
fetch: ## download the latest Discogs dump into data/
	python scripts/fetch_discogs.py

parse: ## parse the dump  (make parse INPUT=data/discogs_*.xml.gz)
	python -m genrespace parse --input "$(INPUT)" --accepted-only

analyze: ## Parquet -> docs/data.js
	python -m genrespace analyze

# ---- dev ----
test: ## run the test suite
	pytest

lint: ## lint with ruff
	ruff check .

fmt: ## auto-format with ruff
	ruff format .

clean: ## remove build artifacts
	rm -rf data/*.parquet .pytest_cache .ruff_cache dist build src/*.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
	cd paper && make clean
