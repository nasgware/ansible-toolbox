from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
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


def check_docker_image(image_name: str = "ansible-toolbox:latest") -> bool:
    assert DOCKER_BIN is not None

    result = subprocess.run(
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
    result = subprocess.run(
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


def get_dockerfile(py_packages: list[str]) -> str:
    try:
        additional_packages = " ".join(
            py_packages + DEFAULT_PYTHON_PACKAGES,
        )

        content = DOCKER_MANIFEST_MANIFEST_TEMPLATE.substitute(
            additional_packages=additional_packages,
        )

        print(content)

        return content
    except RuntimeError as e:
        print(f"Error reading Dockerfile: {e!s}")
        return ""


def ensure_docker_image(py_packages: list[str]) -> None:
    if not check_docker_image():
        print("Ansible Toolbox Docker image not found. Building...")
        dockerfile_content = get_dockerfile(py_packages)

        if not dockerfile_content:
            msg = "Failed to read Dockerfile from package"
            raise RuntimeError(msg)

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".dockerfile",
        ) as tmp:
            tmp.write(dockerfile_content)
            tmp.flush()
            build_docker_image(tmp.name)

        os.unlink(tmp.name)

        print("Ansible Toolbox Docker image built successfully.")


def execute(arguments: list[str]) -> None:
    assert DOCKER_BIN is not None
    print("Executing Docker command:", " ".join(arguments))
    os.execvp(DOCKER_BIN, arguments)  # noqa: S606


def translate_path(path: str) -> str:
    abs_path = os.path.abspath(path)
    workspace_path = os.path.abspath(os.getcwd())

    if abs_path.startswith(workspace_path):
        return f"/workspace{abs_path[len(workspace_path):]}"

    msg = (
        f"Path {path} is outside the current workspace and cannot be "
        "accessed in the container."
    )

    raise ValueError(msg)


def prepare_arguments(
    arguments: list[str],
    *,
    interactive: bool,
    extra_volumes: list[str],
    extra_envs: list[str],
) -> list[str]:
    docker_cmd = ["docker", "run"]

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
        "-v", f"{os.getcwd()}:/workspace:ro,z",
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
        nargs="*",  # Changed from '+' to '*' to allow empty command when --at-help is used
        help="The Ansible command to run",
    )
    parser.add_argument(
        "--at-i",
        dest="interactive",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--at-py-package",
        dest="py_packages",
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
        print(
            "Error: Docker is not installed or not in PATH",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        parser = parse_arguments()

        # Parse known args first to check for --at-help
        known_args, _ = parser.parse_known_args()

        if known_args.help:
            parser.print_help()
            sys.exit(0)

        # If --at-help is not present, parse all args
        args = parser.parse_args()

        if not args.command:
            parser.error("the following arguments are required: command")

        ensure_docker_image(args.py_packages)

        docker_args = prepare_arguments(
            args.command,
            interactive=args.interactive,
            extra_volumes=args.volumes,
            extra_envs=args.envs,
        )

        execute(docker_args)

    except ValueError as e:
        print(f"Error: {e!s}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"An unexpected error occurred: {e!s}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
