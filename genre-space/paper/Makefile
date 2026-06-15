# Builds paper.pdf from paper.tex. Requires TeX Live.
# Run from repo root:  make paper
# Or from paper/:      make
.PHONY: all clean figures

PAPER = paper
FIGDIR = figures

all: $(PAPER).pdf

# Regenerate figures + numbers.tex from current data before building
figures:
	cd .. && python -m genrespace figures

$(PAPER).pdf: $(PAPER).tex references.bib numbers.tex $(FIGDIR)/*.pdf
	pdflatex -interaction=nonstopmode $(PAPER).tex
	bibtex $(PAPER)
	pdflatex -interaction=nonstopmode $(PAPER).tex
	pdflatex -interaction=nonstopmode $(PAPER).tex

numbers.tex: ../viz/data.js
	cd .. && python -m genrespace figures

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.fls *.fdb_latexmk
