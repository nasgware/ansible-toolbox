from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .config import (
    DEFAULT_IMAGE_NAME,
    DEFAULT_PYTHON_PACKAGES,
    DOCKERFILE_TEMPLATE,
)

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    from argparse import Namespace
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class ContainerRunnerProtocol(Protocol):
    """Protocol for container runner operations."""

    def get_binary(self: Self) -> str:
        """Get container runtime binary path."""

    def build_image(
        self: Self,
        dockerfile_path: str,
        image_name: str = "",
    ) -> None:
        """Build container image from Dockerfile."""

    def is_image_present(self: Self, image_name: str = "") -> bool:
        """Check if container image exists."""

    def prepare_run_args(
        self: Self,
        command: Sequence[str],
        *,
        interactive: bool = False,
        volumes: Sequence[str] | None = None,
        env_vars: Sequence[str] | None = None,
    ) -> list[str]:
        """Prepare container run command arguments."""


class DockerRunner(ContainerRunnerProtocol):
    """Docker container runtime implementation."""

    def __init__(self: Self) -> None:
        """Initialize Docker runner."""
        self._binary = self._find_binary()

    def _find_binary(self: Self) -> str:
        """Find Docker binary in PATH."""
        import shutil

        binary = shutil.which("docker")
        if not binary:
            msg = "Docker is not installed or not in PATH"
            raise RuntimeError(msg)
        return binary

    def get_binary(self: Self) -> str:
        """Get Docker binary path."""
        return self._binary

    def is_image_present(
        self: Self,
        image_name: str = DEFAULT_IMAGE_NAME,
    ) -> bool:
        """Check if Docker image exists locally."""
        result = subprocess.run(  # noqa: S603
            [self._binary, "image", "inspect", image_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    def build_image(
        self: Self,
        dockerfile_path: str,
        image_name: str = DEFAULT_IMAGE_NAME,
    ) -> None:
        """Build Docker image from Dockerfile."""
        logger.info("Building Docker image %s...", image_name)

        result = subprocess.run(  # noqa: S603
            [
                self._binary,
                "build",
                "-t",
                image_name,
                "-f",
                dockerfile_path,
                ".",
            ],
            check=False,
        )

        if result.returncode != 0:
            msg = "Failed to build Docker image"
            raise RuntimeError(msg)

        logger.info("Docker image built successfully")

    def prepare_run_args(
        self: Self,
        command: Sequence[str],
        *,
        interactive: bool = False,
        volumes: Sequence[str] | None = None,
        env_vars: Sequence[str] | None = None,
    ) -> list[str]:
        """Prepare Docker run command arguments."""
        cmd = [self._binary, "run"]

        if interactive:
            cmd.append("-it")

        # fmt: off
        cmd += [
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

        if volumes:
            cmd.extend(f"-v {v}" for v in volumes)

        if env_vars:
            cmd.extend(f"-e {e}" for e in env_vars)

        cmd += [DEFAULT_IMAGE_NAME, "/bin/sh"]

        if not interactive:
            translated_cmd = [
                translate_path(arg) if Path(arg).exists() else arg
                for arg in command
            ]
            cmd += ["-c", f"cd /workspace && {' '.join(translated_cmd)}"]

        return cmd


class AnsibleToolbox:
    """Main application class for ansible-toolbox."""

    def __init__(
        self: Self,
        container_runner: ContainerRunnerProtocol,
    ) -> None:
        """Initialize with container runner."""
        self.runner = container_runner

    def ensure_image(self: Self, python_packages: Sequence[str]) -> None:
        """Ensure container image exists, building if needed."""
        if not self.runner.is_image_present(DEFAULT_IMAGE_NAME):
            logger.info("Building Ansible Toolbox image...")
            dockerfile = self._generate_dockerfile(python_packages)

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".dockerfile",
                encoding="utf-8",
            ) as tmp:
                tmp.write(dockerfile)
                tmp.flush()
                self.runner.build_image(tmp.name, DEFAULT_IMAGE_NAME)

    def _generate_dockerfile(
        self: Self,
        python_packages: Sequence[str],
    ) -> str:
        """Generate Dockerfile content."""
        try:
            packages = " ".join(
                list(python_packages) + DEFAULT_PYTHON_PACKAGES
            )
            return DOCKERFILE_TEMPLATE.substitute(
                additional_packages=packages,
            )
        except ValueError as e:
            msg = "Failed to generate Dockerfile"
            raise RuntimeError(msg) from e

    def run(self: Self, args: Namespace) -> None:
        """Run ansible command in container."""
        self.ensure_image(args.additional_python_packages)

        run_args = self.runner.prepare_run_args(
            args.command,
            interactive=args.interactive,
            volumes=args.volumes,
            env_vars=args.envs,
        )

        logger.info("Executing: %s", " ".join(run_args))
        os.execvp(self.runner.get_binary(), run_args)  # noqa: S606


def translate_path(path: str) -> str:
    """Translate local path to container path."""
    abs_path = Path(path).resolve()
    workspace_path = Path.cwd().resolve()

    try:
        relative_path = abs_path.relative_to(workspace_path)
        return str(Path("/workspace") / relative_path)
    except ValueError as e:
        msg = (
            f"Path {path!s} is outside the current workspace and cannot "
            "be accessed in the container"
        )
        raise ValueError(msg) from e
