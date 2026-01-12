# ABOUTME: Kale Development Makefile - unified task automation.
# ABOUTME: Use 'make dev' to set up the development environment.

.PHONY: help dev install \
        test test-backend test-backend-unit test-labextension test-e2e test-e2e-install \
        lint lint-backend lint-labextension format-labextension \
        build-backend build-labextension \
        kfp-build kfp-serve kfp-compile kfp-run \
        clean clean-venv lock lock-upgrade check-uv \
        jupyter jupyter-kfp watch-labextension

UV := uv
# jlpm is a yarn wrapper provided by JupyterLab - use it for extension development
JLPM := $(UV) run jlpm

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BLUE)Kale Development Commands$(NC)\n\nUsage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

check-uv: ## Verify uv is installed
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "$(YELLOW)uv not found. Installing...$(NC)"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}

##@ Installation

# Dev version used for local development (matches KFP_DEV_VERSION)
DEV_VERSION ?= 2.0.0a1

dev: check-uv ## Set up development environment
	@echo "$(BLUE)Setting up Kale development environment...$(NC)"
	$(UV) sync --all-packages --all-extras
	cd labextension && $(JLPM) install
	cd labextension && $(JLPM) build
	$(UV) run jupyter labextension develop ./labextension --overwrite
	@command -v pre-commit >/dev/null 2>&1 && pre-commit install || echo "$(YELLOW)Tip: Install pre-commit for git hooks (pip install pre-commit)$(NC)"
	@echo "$(GREEN)Setup complete! Run 'make jupyter' to start JupyterLab$(NC)"

install: dev ## Alias for dev

##@ Testing

test: test-backend test-labextension ## Run all tests

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	$(UV) run pytest backend/kale/tests -vv

test-backend-unit: ## Run backend unit tests only
	@echo "$(BLUE)Running backend unit tests...$(NC)"
	$(UV) run pytest backend/kale/tests/unit_tests -vv

test-labextension: ## Run labextension tests
	@echo "$(BLUE)Running labextension tests...$(NC)"
	cd labextension && $(JLPM) test

test-e2e-install: ## Install Playwright browsers (run once)
	@echo "$(BLUE)Installing Playwright dependencies...$(NC)"
	cd labextension/ui-tests && $(JLPM) install
	cd labextension/ui-tests && $(JLPM) playwright install
	@echo "$(GREEN)Playwright installed!$(NC)"

test-e2e: ## Run Playwright e2e tests (experimental)
	@echo "$(BLUE)Running Playwright e2e tests...$(NC)"
	@echo "$(YELLOW)Note: e2e tests may timeout due to extension kernel startup$(NC)"
	cd labextension/ui-tests && $(JLPM) playwright test

##@ Linting

lint: lint-backend lint-labextension ## Run all linters

lint-backend: ## Lint backend code (ruff)
	@echo "$(BLUE)Linting backend...$(NC)"
	$(UV) run ruff check backend
	$(UV) run ruff format --check backend

lint-labextension: ## Lint labextension code (eslint + prettier)
	@echo "$(BLUE)Linting labextension...$(NC)"
	cd labextension && $(JLPM) lint:check

format-labextension: ## Format labextension code
	cd labextension && $(JLPM) prettier && $(JLPM) eslint

##@ Building

build-backend: ## Build backend wheel
	@echo "$(BLUE)Building backend wheel with version $(DEV_VERSION)...$(NC)"
	cd backend && SETUPTOOLS_SCM_PRETEND_VERSION=$(DEV_VERSION) $(UV) build
	@echo "$(GREEN)Wheel built: backend/dist/$(NC)"

build-labextension: ## Build labextension wheel
	@echo "$(BLUE)Building labextension...$(NC)"
	cd labextension && $(JLPM) build:prod
	cd labextension && $(UV) build
	@echo "$(GREEN)Labextension wheel built: labextension/dist/$(NC)"

##@ KFP Development (replaces devpi workflow)

KFP_WHEEL_DIR ?= $(CURDIR)/.kfp-wheels
KFP_PORT ?= 8765
KFP_DEV_VERSION ?= $(DEV_VERSION)

kfp-build: ## Build wheel for KFP cluster testing (fixed version for reproducibility)
	@echo "$(BLUE)Building wheel with version $(KFP_DEV_VERSION)...$(NC)"
	rm -f dist/kubeflow_kale-*.whl
	cd backend && SETUPTOOLS_SCM_PRETEND_VERSION=$(KFP_DEV_VERSION) $(UV) build
	@# Create PEP 503 compliant simple index structure
	rm -rf $(KFP_WHEEL_DIR)
	mkdir -p $(KFP_WHEEL_DIR)/kubeflow-kale
	cp dist/kubeflow_kale-*.whl $(KFP_WHEEL_DIR)/kubeflow-kale/
	@# Generate index files for pip simple API
	@echo '<!DOCTYPE html><html><body><a href="kubeflow-kale/">kubeflow-kale</a></body></html>' > $(KFP_WHEEL_DIR)/index.html
	@cd $(KFP_WHEEL_DIR)/kubeflow-kale && for f in *.whl; do echo "<a href=\"$$f\">$$f</a><br>"; done > index.html
	@echo "$(GREEN)Wheel ready at $(KFP_WHEEL_DIR)$(NC)"

kfp-serve: kfp-build ## Serve wheel via HTTP for Kind/Docker clusters
	@echo "$(BLUE)Starting wheel server on port $(KFP_PORT)...$(NC)"
	@echo ""
	@echo "$(YELLOW)Set these environment variables before compiling:$(NC)"
	@echo "  export KALE_PIP_INDEX_URLS=\"http://host.docker.internal:$(KFP_PORT),https://pypi.org/simple\""
	@echo "  export KALE_PIP_TRUSTED_HOSTS=\"host.docker.internal\""
	@echo ""
	cd $(KFP_WHEEL_DIR) && python3 -m http.server $(KFP_PORT)

kfp-compile: ## Compile notebook with local wheel (usage: make kfp-compile NB=path/to/notebook.ipynb)
	@test -n "$(NB)" || { echo "$(YELLOW)Usage: make kfp-compile NB=path/to/notebook.ipynb$(NC)"; exit 1; }
	@echo "$(YELLOW)Make sure 'make kfp-serve' is running in another terminal$(NC)"
	SETUPTOOLS_SCM_PRETEND_VERSION=$(KFP_DEV_VERSION) \
	KALE_PIP_INDEX_URLS="http://host.docker.internal:$(KFP_PORT),https://pypi.org/simple" \
	KALE_PIP_TRUSTED_HOSTS="host.docker.internal" \
	$(UV) run kale --nb $(NB)

kfp-run: ## Compile and run on KFP with local wheel (usage: make kfp-run NB=... KFP_HOST=...)
	@test -n "$(NB)" || { echo "$(YELLOW)Usage: make kfp-run NB=path/to/notebook.ipynb KFP_HOST=http://localhost:8080$(NC)"; exit 1; }
	@test -n "$(KFP_HOST)" || { echo "$(YELLOW)Error: KFP_HOST not set$(NC)"; exit 1; }
	@echo "$(YELLOW)Make sure 'make kfp-serve' is running in another terminal$(NC)"
	SETUPTOOLS_SCM_PRETEND_VERSION=$(KFP_DEV_VERSION) \
	KALE_PIP_INDEX_URLS="http://host.docker.internal:$(KFP_PORT),https://pypi.org/simple" \
	KALE_PIP_TRUSTED_HOSTS="host.docker.internal" \
	$(UV) run kale --nb $(NB) --kfp_host $(KFP_HOST) --run_pipeline

##@ Cleanup

clean: ## Clean all build artifacts
	@echo "$(BLUE)Cleaning...$(NC)"
	rm -rf .venv
	rm -rf dist backend/dist backend/*.egg-info
	rm -rf labextension/dist labextension/*.egg-info
	rm -rf labextension/lib labextension/node_modules
	rm -rf labextension/kubeflow_kale_labextension/labextension
	rm -rf .kfp-wheels .kale
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(NC)"

clean-venv: ## Remove virtual environment only
	rm -rf .venv

##@ Lockfile Management

lock: check-uv ## Update uv.lock
	$(UV) lock

lock-upgrade: check-uv ## Upgrade all dependencies and update lock
	$(UV) lock --upgrade

##@ Development Helpers

jupyter: ## Start JupyterLab
	$(UV) run jupyter lab

jupyter-kfp: ## Start JupyterLab with KFP dev environment (run kfp-serve first!)
	@echo "$(YELLOW)Make sure 'make kfp-serve' is running in another terminal$(NC)"
	SETUPTOOLS_SCM_PRETEND_VERSION=$(KFP_DEV_VERSION) \
	KALE_PIP_INDEX_URLS="http://host.docker.internal:$(KFP_PORT),https://pypi.org/simple" \
	KALE_PIP_TRUSTED_HOSTS="host.docker.internal" \
	$(UV) run jupyter lab

watch-labextension: ## Watch labextension for changes (run in separate terminal)
	cd labextension && $(JLPM) watch
