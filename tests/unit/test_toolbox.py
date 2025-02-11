from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from ansible_toolbox.config import DEFAULT_IMAGE_NAME
from ansible_toolbox.core import AnsibleToolbox, ContainerRunnerProtocol

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class MockContainerRunner(ContainerRunnerProtocol):
    """Mock container runner for testing."""

    def get_binary(self) -> str:
        """Get mock binary path."""
        return "/mock/binary"

    def build_image(
        self,
        dockerfile_path: str,
        image_name: str = "",
    ) -> None:
        """Mock build image."""

    def is_image_present(self, image_name: str = "") -> bool:
        """Mock image presence check."""
        return False

    def prepare_run_args(
        self,
        command: list[str],
        *,
        interactive: bool = False,
        volumes: list[str] | None = None,
        env_vars: list[str] | None = None,
    ) -> list[str]:
        """Mock prepare run arguments."""
        return ["/mock/binary", "run", "container"]


@pytest.fixture
def mock_runner() -> mock.MagicMock:
    """Create a mock container runner."""
    mock_runner = mock.MagicMock(spec=ContainerRunnerProtocol)
    mock_runner.get_binary.return_value = "/mock/binary"
    mock_runner.prepare_run_args.return_value = [
        "/mock/binary",
        "run",
        "container",
    ]
    return mock_runner


@pytest.fixture
def toolbox(mock_runner: mock.MagicMock) -> AnsibleToolbox:
    """Create an AnsibleToolbox instance with mock runner."""
    return AnsibleToolbox(mock_runner)


def test_toolbox_init() -> None:
    """Test AnsibleToolbox initialization."""
    mock_runner = MockContainerRunner()
    toolbox = AnsibleToolbox(mock_runner)
    assert toolbox.runner == mock_runner


def test_ensure_image_builds_when_missing(
    toolbox: AnsibleToolbox,
    mock_runner: mock.MagicMock,
    mocker: MockerFixture,
) -> None:
    """Test image building when not present."""
    mock_runner.is_image_present.return_value = False

    # Mock NamedTemporaryFile to capture the Dockerfile content
    mock_temp_file = mocker.MagicMock()
    mock_temp_file.__enter__.return_value.name = "/tmp/mock/Dockerfile"
    mock_temp_file.__enter__.return_value.write = mocker.MagicMock()

    mocker.patch(
        "tempfile.NamedTemporaryFile",
        return_value=mock_temp_file,
    )

    toolbox.ensure_image(["package1", "package2"])

    # Verify image presence check
    mock_runner.is_image_present.assert_called_once_with(
        DEFAULT_IMAGE_NAME
    )

    # Verify Dockerfile content
    dockerfile_content = (
        mock_temp_file.__enter__.return_value.write.call_args[0][0]
    )
    assert "package1" in dockerfile_content
    assert "package2" in dockerfile_content

    # Verify image build
    mock_runner.build_image.assert_called_once_with(
        "/tmp/mock/Dockerfile",
        DEFAULT_IMAGE_NAME,
    )


def test_ensure_image_skips_when_exists(
    toolbox: AnsibleToolbox,
    mock_runner: mock.MagicMock,
) -> None:
    """Test image building is skipped when present."""
    mock_runner.is_image_present.return_value = True

    toolbox.ensure_image([])

    mock_runner.is_image_present.assert_called_once_with(
        DEFAULT_IMAGE_NAME
    )
    mock_runner.build_image.assert_not_called()


def test_run_basic_command(
    toolbox: AnsibleToolbox,
    mock_runner: mock.MagicMock,
    mocker: MockerFixture,
) -> None:
    """Test running a basic command."""
    mock_execvp = mocker.patch("os.execvp")
    args = mock.MagicMock(
        command=["ansible-playbook", "site.yml"],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )

    toolbox.run(args)

    mock_runner.prepare_run_args.assert_called_once_with(
        ["ansible-playbook", "site.yml"],
        interactive=False,
        volumes=[],
        env_vars=[],
    )
    mock_execvp.assert_called_once_with(
        "/mock/binary",
        ["/mock/binary", "run", "container"],
    )


def test_run_with_options(
    toolbox: AnsibleToolbox,
    mock_runner: mock.MagicMock,
    mocker: MockerFixture,
) -> None:
    """Test running command with additional options."""
    mock_execvp = mocker.patch("os.execvp")
    args = mock.MagicMock(
        command=["ansible-playbook", "playbook.yml"],
        interactive=True,
        additional_python_packages=["package1", "package2"],
        volumes=["/host:/container"],
        envs=["VAR=value"],
    )
    mock_runner.prepare_run_args.return_value = [
        "/mock/binary",
        "run",
        "-it",
        "container",
    ]

    toolbox.run(args)

    mock_runner.prepare_run_args.assert_called_once_with(
        ["ansible-playbook", "playbook.yml"],
        interactive=True,
        volumes=["/host:/container"],
        env_vars=["VAR=value"],
    )
    mock_execvp.assert_called_once_with(
        "/mock/binary",
        ["/mock/binary", "run", "-it", "container"],
    )


def test_run_error_handling(
    toolbox: AnsibleToolbox,
    mock_runner: mock.MagicMock,
) -> None:
    """Test error handling during run."""
    args = mock.MagicMock(
        command=["ansible-playbook", "site.yml"],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )

    mock_runner.is_image_present.side_effect = RuntimeError("Test error")

    with pytest.raises(RuntimeError, match="Test error"):
        toolbox.run(args)

    mock_runner.is_image_present.assert_called_once()
    mock_runner.prepare_run_args.assert_not_called()
