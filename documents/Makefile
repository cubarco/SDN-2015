TEX = xelatex -8bit -output-directory=output
BIBTEX = bibtex

SDN2015: SDN2015.pdf

SDN2015.pdf: SDN2015.tex
	${TEX} $<
	${BIBTEX} $(basename $<)
	${TEX} $<
	${TEX} $<

clean:
	rm -rf output/{*.out,*.lot,*.log,*.lof,*.toc,*.thm,*.aux} *.blg *.bbl


.PHONY: all
all: SDN2015
