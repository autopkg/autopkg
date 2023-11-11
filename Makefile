.PHONY: test

test: .venv
	@echo "Running test"
	@poetry run python scripts/run_tests.py

install-hooks: .venv
	@poetry run pre-commit install -f --install-hooks

.venv:
	@poetry install

clean:
	@rm -rf dist/
	@rm -rf .venv/
