SRC = src
EXE = $(SRC)
VENV = .venv
PYTHON = $(VENV)/bin/python3
UVRUN= uv run python
CACHE_DIR = $(CURDIR)/.uv_cache


TRASH = $(SRC)/__pycache__ $(VENV) .mypy_cache __pycache__ data/output

FLAGS = --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs --exclude moulinette

# ANSI codes
GREEN = \033[0;32m
RED = \033[0;31m
YELLOW = \033[0;33m
BOLD = \033[1m

SUCCESS = \033[1;92m
RESET = \033[0m

install:
	@echo "$(BOLD)Initializing project environment:$(RESET)"

	@echo "$(YELLOW)Creating virtual environment...$(RESET)"
	@UV_CACHE_DIR="$(CACHE_DIR)" UV_LINK_MODE=copy \
		uv venv --python 3.10 $(VENV) --clear > /dev/null 2>&1
	@echo "$(GREEN)Virtual environment setup complete$(RESET)"

	@bash -c '\
		UV_CACHE_DIR="$(CACHE_DIR)" UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT="$(VENV)" \
		uv sync > /dev/null 2>&1 & pid=$$!; \
		spin="-\|/"; i=0; \
		while kill -0 $$pid 2>/dev/null; do \
			printf "\r$(YELLOW)[%s] Installing dependencies...$(RESET)" "$${spin:$$((i % 4)):1}"; \
			i=$$((i + 1)); \
			sleep 0.1; \
		done; \
		wait $$pid; \
		printf "\r$(GREEN)Installing dependencies... done$(RESET)\n"'

	@echo "$(GREEN)All dependencies successfully installed$(RESET)"
	@echo "\n$(SUCCESS)Project can now be run safely!$(RESET)"

lint:
	@echo "$(BOLD)Verifying project source code:$(RESET)"

	@echo "$(YELLOW)Running flake8...$(RESET)"
	@$(PYTHON) -m flake8 src
	@echo "$(GREEN)No norm errors found$(RESET)"

	@echo "\n$(YELLOW)Running mypy...$(RESET)"
	@$(PYTHON) -m mypy . $(FLAGS)
	@echo "$(GREEN)No typing errors found$(RESET)"

	@echo "\n$(SUCCESS)Success: no errors found in source code!$(RESET)"

mypy:
	@echo "\n$(YELLOW)Running mypy...$(RESET)"
	@$(PYTHON) -m mypy . $(FLAGS)
	@echo "$(GREEN)No typing errors found$(RESET)"

debug:
	@$(PYTHON) -m pdb -m $(EXE) $(CONFIG)

clean:
	@echo "$(YELLOW)Initiating cleanup operation...$(RESET)"
	@found=0; \
	for i in $(TRASH); do \
		if [ -d "$$i" ]; then \
			echo " - Removed directory $(RED)'$$i'$(RESET)"; \
			found=1; \
		elif [ -e "$$i" ]; then \
			echo " - Removed file $(RED)'$$i'$(RESET)"; \
			found=1; \
		fi; \
	done; \
	if [ $$found -eq 0 ]; then \
		echo "$(GREEN)Nothing to clean :)$(RESET)"; \
	fi
	@rm -rf $(TRASH)
	@echo "$(SUCCESS)\nCleanup complete!$(RESET)"

clean_cache:
	@echo "$(YELLOW)Initiating cleanup cache operation...$(RESET)"
	@echo "$(RED) Removed: $(CACHE_DIR) $(HF_CACHE_DIR)$(RESET)"
	@rm -rf $(CACHE_DIR) $(HF_CACHE_DIR)
	@echo "$(SUCCESS)\nCleanup cache complete!$(RESET)"