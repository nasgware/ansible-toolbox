from pathlib import Path
from subprocess import CompletedProcess

import pytest
from pytest_mock import MockerFixture

from ansible_toolbox.config import DEFAULT_IMAGE_NAME
from ansible_toolbox.core import DockerRunner


@pytest.fixture
def docker_runner() -> DockerRunner:
    """Create a DockerRunner instance."""
    return DockerRunner()


def test_get_binary_success(mocker: MockerFixture) -> None:
    """Test successful binary path retrieval."""
    mocker.patch("shutil.which", return_value="/usr/bin/docker")
    runner = DockerRunner()
    assert runner.get_binary() == "/usr/bin/docker"


def test_get_binary_not_found(mocker: MockerFixture) -> None:
    """Test binary path retrieval when docker is not installed."""
    mocker.patch("shutil.which", return_value=None)
    with pytest.raises(RuntimeError, match="Docker is not installed"):
        DockerRunner()


def test_is_image_present_success(
    docker_runner: DockerRunner,
    mocker: MockerFixture,
) -> None:
    """Test successful image presence check."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = CompletedProcess("", 0)

    assert docker_runner.is_image_present() is True
    mock_run.assert_called_once_with(
        [
            docker_runner.get_binary(),
            "image",
            "inspect",
            DEFAULT_IMAGE_NAME,
        ],
        stdout=mocker.ANY,
        stderr=mocker.ANY,
        check=False,
    )


def test_is_image_present_failed(
    docker_runner: DockerRunner,
    mocker: MockerFixture,
) -> None:
    """Test failed image presence check."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = CompletedProcess("", 1)

    assert docker_runner.is_image_present() is False


def test_build_image_success(
    docker_runner: DockerRunner,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test successful Docker image build."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = CompletedProcess("", 0)

    docker_runner.build_image(str(tmp_path))
    mock_run.assert_called_once()


def test_build_image_failed(
    docker_runner: DockerRunner,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test failed Docker image build."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = CompletedProcess("", 1)

    with pytest.raises(RuntimeError, match="Failed to build Docker image"):
        docker_runner.build_image(str(tmp_path))


def test_prepare_run_args_interactive(
    docker_runner: DockerRunner,
    mocker: MockerFixture,
) -> None:
    """Test argument preparation for interactive mode."""
    command = ["some_command"]
    volumes = ["/path/to/volume1", "/path/to/volume2"]
    env_vars = ["ENV1=value1", "ENV2=value2"]

    mocker.patch(
        "pathlib.Path.cwd",
        return_value=Path("/mock/cwd"),
    )

    result = docker_runner.prepare_run_args(
        command,
        interactive=True,
        volumes=volumes,
        env_vars=env_vars,
    )

    assert result[:2] == [docker_runner.get_binary(), "run"]
    assert "-it" in result
    assert "--rm" in result
    assert "--name" in result
    assert "-v" in result
    assert "/mock/cwd:/workspace:ro,z" in result
    for vol in volumes:
        assert f"-v {vol}" in result
    for env in env_vars:
        assert f"-e {env}" in result
    assert DEFAULT_IMAGE_NAME in result
    assert result[-1] == "/bin/sh"


def test_prepare_run_args_non_interactive(
    docker_runner: DockerRunner,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """Test argument preparation for non-interactive mode."""
    command = ["some_command", "/path/to/file"]

    mocker.patch(
        "pathlib.Path.cwd",
        return_value=tmp_path,
    )

    result = docker_runner.prepare_run_args(
        command,
        interactive=False,
    )

    assert result[:2] == [docker_runner.get_binary(), "run"]
    assert "-it" not in result
    assert "-c" in result
    assert "cd /workspace" in result[result.index("-c") + 1]
    assert "some_command" in result[result.index("-c") + 1]
