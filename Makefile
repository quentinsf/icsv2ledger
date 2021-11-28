.PHONY: all
all: test lint

.PHONY: test
test:
	$(MAKE) -C tests

lint_files=icsv2ledger.py tests

.PHONY: lint
lint:
	@echo "=== flake8 ==="
	flake8 $(lint_files)
	@echo "=== isort ==="
	isort --check --diff $(lint_files)
	@echo "=== yapf ==="
	yapf --recursive --diff $(lint_files)

.PHONY: fixlint
fixlint:
	@echo "=== fixing isort ==="
	isort --quiet --recursive $(lint_files)
	@echo "=== fixing yapf ==="
	yapf --recursive --in-place $(lint_files)


requirements.txt: requirements.in
	pip-compile -v
