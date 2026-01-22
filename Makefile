.PHONY: tests

tests:
	pytest -x --cov=custom_components/signal_gateway --cov-report=term-missing --cov-report=xml:coverage.xml tests/
