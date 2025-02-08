#!/usr/bin/env just --justfile

[private]
ensure-pdm:
    #!/usr/bin/env sh
    if ! command -v python >/dev/null 2>&1; then
        echo "pyhton must be available in the path"
        exit 1
    fi

    $(which python) -m  ensurepip --upgrade

    if ! command -v pdm >/dev/null 2>&1; then
        echo "Installing pdm..."
        $(which python) -m pip install pdm  
    fi

[private]
ensure-pre-commit:
    #!/usr/bin/env sh
    if ! command -v pre-commit >/dev/null 2>&1; then
        echo "Installing pre-commit..."
        pdm add --dev pre-commit 
    fi

    if ! command -v gitlint >/dev/null 2>&1; then
        echo "Installing pre-commit..."
        pdm add --dev gitlint
    fi

    pre-commit install --hook-type commit-msg

binary_name := "at"
package_name := "ansible_toolbox"

default:
    @just --list

setup-dev:
    pdm install --dev
    pdm install

test:
    pdm run pytest;

build:
    pdm build

clean:
    rm -rf build dist
    pdm run pyclean .

run *args:
    pdm run {{binary_name}} {{args}}

ci: clean setup-dev lint type-check test build

test-python VERSION:
    pdm use {{VERSION}}
    pdm install --dev
    pdm run pytest

setup-hooks:
    pre-commit install

format:
    ruff format .
    ruff check . --fix

lint:
    ruff check .
    ruff format . --check

type-check:
    pdm run mypy --config-file mypy.ini

check: lint type-check test

shell:
    pdm run python

init: ensure-pdm
    pdm .venv create
    just setup-dev
    just ensure-pre-commit
    just setup-hooks
