.PHONY: tests run

tests:
	PYTHONPATH=./ pytest -x -vv --log-level=DEBUG --doctest-modules --cov=custom_components/signal_gateway --cov-report=term --cov-report=xml:coverage.xml custom_components/signal_gateway tests/

run:
	@echo "🚀 Démarrage de Home Assistant..."
	python -m homeassistant -c config --debug

