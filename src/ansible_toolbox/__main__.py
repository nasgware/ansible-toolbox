from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from string import Template

DOCKER_BIN = shutil.which("docker")


class CustomTemplate(Template):
    delimiter = "%"


DOCKER_MANIFEST_MANIFEST_TEMPLATE = CustomTemplate("""
FROM docker.io/alpine:latest

ENV PYTHONUNBUFFERED=1 \\
    PYTHONIOENCODING=UTF-8 \\
    PIP_NO_CACHE_DIR=yes \\
    VIRTUAL_ENV=/install/.venv \\
    PATH="/install/.venv/bin:$PATH"

RUN apk add --no-cache \\
    ca-certificates \\
    openssh \\
    git \\
    python3 \\
    py3-pip \\
    && python3 -m venv $VIRTUAL_ENV \\
    && pip install --no-cache-dir ansible %additional_packages \\
    && rm -rf /tmp/* /var/cache/apk/* /root/.cache
""")

DEFAULT_PYTHON_PACKAGES = ["requests==2.32.3", "docker==7.1.0 "]


def is_docker_image_present(
    image_name: str = "ansible-toolbox:latest",
) -> bool:
    assert DOCKER_BIN is not None

    result = subprocess.run(  # noqa: S603
        [DOCKER_BIN, "image", "inspect", image_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def build_docker_image(
    dockerfile_path: str,
    image_name: str = "ansible-toolbox:latest",
) -> None:
    assert DOCKER_BIN is not None

    print(f"Building Docker image {image_name}...")

    # fmt: off
    result = subprocess.run(  # noqa: S603
        [
            DOCKER_BIN, "build",
            "-t", image_name,
            "-f", dockerfile_path, ".",
        ],
        check=True,
    )
    # fmt: on

    if result.returncode != 0:
        msg = "Failed to build Docker image"
        raise RuntimeError(msg)


def get_dockerfile(additional_python_packages: list[str]) -> str:
    try:
        additional_packages = " ".join(
            additional_python_packages + DEFAULT_PYTHON_PACKAGES,
        )

        return DOCKER_MANIFEST_MANIFEST_TEMPLATE.substitute(
            additional_packages=additional_packages,
        )

    except ValueError as e:
        msg = "Failed to generate the Dockerfile"
        raise RuntimeError(msg) from e


def ensure_docker_image(additional_python_packages: list[str]) -> None:
    print("Ansible Toolbox Docker image not found. Building...")
    dockerfile_content = get_dockerfile(additional_python_packages)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".dockerfile",
        encoding="utf-8",
    ) as tmp:
        tmp.write(dockerfile_content)
        tmp.flush()
        build_docker_image(tmp.name)

    print("Docker image built successfully.")


def execute(arguments: list[str]) -> None:
    assert DOCKER_BIN is not None
    print("Executing Docker command:", " ".join(arguments))
    os.execvp(DOCKER_BIN, arguments)  # noqa: S606


def translate_path(path: str) -> str:
    abs_path = Path(path).resolve()
    workspace_path = Path.cwd().resolve()

    try:
        relative_path = abs_path.relative_to(workspace_path)
        return str(Path("/workspace") / relative_path)
    except ValueError as e:
        msg = (
            f"Path {path!s} is outside the current workspace and cannot "
            "be accessed in the container."
        )
        raise ValueError(msg) from e


def prepare_arguments(
    arguments: list[str],
    *,
    interactive: bool,
    extra_volumes: list[str],
    extra_envs: list[str],
) -> list[str]:
    assert DOCKER_BIN is not None
    docker_cmd = [DOCKER_BIN, "run"]

    if interactive:
        docker_cmd.append("-it")

    # fmt: off
    docker_cmd += [
        "--rm",
        "--name", "ansible-toolbox",
        "--network", "host",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--cap-drop", "NET_BIND_SERVICE",
        "--cap-drop", "SETUID",
        "--cap-drop", "SETGID",
        "--security-opt", "no-new-privileges",
        "-v", "/etc/passwd:/etc/passwd:ro,z",
        "-v", "/etc/group:/etc/group:ro,z",
        "-v", "/tmp:/tmp:z",
        "-v", "/var/tmp:/var/tmp:z",
        "-v", f"{Path.cwd()}:/workspace:ro,z",
        "-e", "HOME=/tmp",
        "-e", "TERM=xterm-256color",
        "-e", "ANSIBLE_LOCAL_TEMP=/tmp",
        "-e", "ANSIBLE_REMOTE_TEMP=/tmp/$(whoami)",
        "-e", "ANSIBLE_STDOUT_CALLBACK=debug",
        "-e", "ANSIBLE_CONFIG=/workspace/ansible.cfg",
        "-e", "ANSIBLE_FORCE_COLOR=1",
    ]
    # fmt: on

    for volume in extra_volumes:
        docker_cmd += ["-v", volume]

    for env in extra_envs:
        docker_cmd += ["-e", env]

    docker_cmd += ["ansible-toolbox:latest", "/bin/sh"]

    if not interactive:
        translated_args = [
            translate_path(arg) if Path(arg).exists() else arg
            for arg in arguments
        ]
        docker_cmd += [
            "-c",
            f"cd /workspace && {' '.join(translated_args)}",
        ]

    return docker_cmd


def parse_arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Ansible commands in a Docker container.",
        add_help=False,
    )
    parser.add_argument(
        "--at-help",
        dest="help",
        action="store_true",
        help="Show this help message and exit",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="The Ansible command to run",
    )
    parser.add_argument(
        "--at-i",
        dest="interactive",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--at-add-py-package",
        dest="additional_python_packages",
        action="append",
        default=[],
        help="Additional python packages to add to the toolbox",
    )
    parser.add_argument(
        "--at-volume",
        dest="volumes",
        action="append",
        default=[],
        help="Additional volumes to mount",
    )
    parser.add_argument(
        "--at-env",
        dest="envs",
        action="append",
        default=[],
        help="Additional environment variables",
    )
    return parser


def main() -> None:
    if DOCKER_BIN is None:
        msg = "Docker is not installed or is not in $PATH"
        raise RuntimeError(msg)

    parser = parse_arguments()

    known_args, _ = parser.parse_known_args()

    if known_args.help:
        parser.print_help()
        return

    args = parser.parse_args()

    if not args.command:
        msg = "Please provide the `command` to be executed"
        raise ValueError(msg)

    if not is_docker_image_present():
        ensure_docker_image(args.additional_python_packages)

    docker_args = prepare_arguments(
        args.command,
        interactive=args.interactive,
        extra_volumes=args.volumes,
        extra_envs=args.envs,
    )

    execute(docker_args)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)

    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        print(f"An unexpected error occurred: {e!s}", file=sys.stderr)
        sys.exit(1)
