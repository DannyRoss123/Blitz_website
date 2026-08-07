PYTHON := python

.PHONY: install scrape build serve test all

install:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt || .venv/Scripts/pip install -r requirements.txt

scrape:
	$(PYTHON) scrape.py

build:
	$(PYTHON) build.py

serve:
	@echo "Open http://localhost:8080/website/ in your browser"
	$(PYTHON) -m http.server 8080

test:
	$(PYTHON) -m pytest tests/ -v

all: build test
