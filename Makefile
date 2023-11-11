.PHONY: test

test: .venv
	@echo "Running tests"
	@poetry run python -m unittest discover

install-hooks: .venv
	@poetry run pre-commit install -f --install-hooks

.venv:
	@poetry install

clean:
	@rm -rf dist/
	@rm -rf .venv/
