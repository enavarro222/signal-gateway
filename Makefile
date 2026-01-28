.PHONY: tests

tests:
	PYTHONPATH=./ pytest -x -vv --log-level=DEBUG --doctest-modules --cov=custom_components/signal_gateway --cov-report=term --cov-report=xml:coverage.xml custom_components/signal_gateway tests/
