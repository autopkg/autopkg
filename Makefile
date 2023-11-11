.PHONY: test install-hooks

test: .venv
	@echo "Running tests"
	@poetry run python -m unittest discover

e2e_tests:
	@echo "Running end-to-end integration tests"
	@bash tests/e2e_tests.sh

install-hooks: .venv
	@poetry run pre-commit install -f --install-hooks

.venv:
	@poetry env use python3.10
	@poetry install

clean:
	@bash scripts/clean.sh
