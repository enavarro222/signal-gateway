.PHONY: tests run install-hooks check lint format

PYTHON_DIR = custom_components/signal_gateway
PYTHON_FILES = $(shell find $(PYTHON_DIR) -name "*.py" -type f)

install-hooks:
	@echo "🔗 Installing git hooks..."
	@mkdir -p .git/hooks
	@cp .githooks/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Git hooks installed"

check: format lint
	@echo "✅ All checks passed"

format:
	@echo "📝 Formatting code with ruff..."
	@ruff format $(PYTHON_FILES)

lint:
	@echo "🔗 Linting with pylint..."
	@pylint $(PYTHON_FILES)
	@echo "🎯 Type checking with mypy..."
	@mypy $(PYTHON_DIR) --ignore-missing-imports

tests:
	PYTHONPATH=./ pytest -x -vv --log-level=DEBUG --doctest-modules --cov=custom_components/signal_gateway --cov-report=term --cov-report=xml:coverage.xml custom_components/signal_gateway tests/

run:
	@echo "🚀 Démarrage de Home Assistant..."
	python -m homeassistant -c config --debug

