binary_name := "at"
package_name := "ansible_toolbox"

default:
    @just --list

install-dev:
    pdm install -d

unit-test:
    pdm run pytest tests/unit

build: unit-test
    pdm build

clean:
    rm -rf build dist
    pdm run pyclean .

create-venv:
    pdm venv create

activate-venv:
    @echo "PDM manages virtual environments automatically."
    @echo "Use 'pdm run <command>' to run commands in the virtual environment."
    @echo "Or use 'pdm shell' to activate the environment in your current shell."

run *args:
    pdm run {{binary_name}} {{args}}

add-dep *args:
    pdm add {{args}}

add-dev-dep *args:
    pdm add -d {{args}}

update-deps:
    pdm update

lock-deps:
    pdm lock

show-outdated:
    pdm show --outdated