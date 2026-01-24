.PHONY: tests

tests:
	PYTHONPATH=./ pytest -x -vv --log-level=DEBUG --cov=custom_components/signal_gateway --cov-report=xml:coverage.xml tests/
