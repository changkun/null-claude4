.PHONY: run demo discover compare lint check install install-dev clean help

# Default simulation
RULE    ?= life
PATTERN ?= glider
ROWS    ?= 40
COLS    ?= 80
SPEED   ?= 0.1

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

run: ## Run the simulator (RULE=life PATTERN=glider ROWS=40 COLS=80 SPEED=0.1)
	python3 life.py --rule $(RULE) --pattern $(PATTERN) --rows $(ROWS) --cols $(COLS) --speed $(SPEED)

demo: ## Run the demo reel (auto-cycles all 28 modes)
	python3 life.py --demo

discover: ## Launch genetic algorithm rule discovery
	python3 life.py --discover

compare: ## Side-by-side comparison (RULE1=life RULE2=highlife)
	python3 life.py --compare $(RULE1) $(RULE2)

install: ## Install as a CLI tool (cellsim)
	pip install .

install-dev: ## Install with development dependencies
	pip install -e ".[fast,dev]"

lint: ## Run linter (ruff)
	ruff check life.py

check: ## Run type checker (mypy)
	mypy life.py

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info __pycache__ .mypy_cache .ruff_cache frames/
