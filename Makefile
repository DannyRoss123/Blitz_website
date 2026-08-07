PYTHON := python

.PHONY: install scrape build serve test all appendix postgres-install postgres-up postgres-down postgres-load

install:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt || .venv/Scripts/pip install -r requirements.txt

scrape:
	$(PYTHON) scrape.py

build:
	$(PYTHON) build.py

serve:
	@echo "Open http://localhost:8080/ in your browser"
	$(PYTHON) -m http.server 8080 --directory website

test:
	$(PYTHON) -m pytest tests/ -v

all: build test

# --- Optional bonus targets (not required for the core submission) ---

# Bonus appendix: cross-check the built CSV against the actual All-Star Game
# box scores; writes data/output/allstar_roster_gaps_appendix.csv.
appendix:
	$(PYTHON) build_appendix.py

# Optional Postgres extra credit (see WRITEUP.md "Bonus: Postgres").
postgres-install:
	.venv/bin/pip install -r requirements-postgres.txt || .venv/Scripts/pip install -r requirements-postgres.txt

postgres-up:
	docker run -d --name blitz-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=blitz_allstars -p 5432:5432 postgres:16

postgres-down:
	docker rm -f blitz-postgres

postgres-load:
	$(PYTHON) load_postgres.py
