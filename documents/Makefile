OUTPUT_DIRECTORY = output
TEX = xelatex -8bit -output-directory=${OUTPUT_DIRECTORY}
BIBTEX = bibtex
TEX_FILE = SDN2015.tex
BASENAME = $(basename ${TEX_FILE})
BIB_FILE = ref-example.bib
CUR_DIR = $(shell pwd)

${BASENAME}: ${BASENAME}.pdf

${BASENAME}.pdf: ${TEX_FILE}
	${TEX} $<
	if ! [ -a ${OUTPUT_DIRECTORY}/${BIB_FILE} ] ; then \
		ln -s ${CUR_DIR}/${BIB_FILE} ${OUTPUT_DIRECTORY}/ ;\
	fi ;
	cd ${OUTPUT_DIRECTORY} && ${BIBTEX} ${BASENAME}
	${TEX} $<
	${TEX} $<

clean:  
	cd ${OUTPUT_DIRECTORY} && make clean
#*.out,*.lot,*.log,*.lof,*.toc,*.thm,*.aux,*.blg,*.bbl,*.bib}


.PHONY: all
all: ${BASENAME}
