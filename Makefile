.PHONY: run scan snapshot test

PLACE ?= Hyderabad

run:
	python -m aether

scan:
	python -m aether scan $(PLACE)

snapshot:
	python -m aether snapshot --places Hyderabad,Tokyo --out docs

test:
	pytest
