from __future__ import annotations

import importlib
from argparse import Namespace
from pathlib import Path
from subprocess import CompletedProcess
from typing import TYPE_CHECKING, Protocol
from unittest import mock

import pytest

import ansible_toolbox.__main__ as main

if TYPE_CHECKING:
    from unittest.mock import Mock

    from pytest_mock import MockerFixture


class MockDockerBinCallable(Protocol):
    def __call__(self, *, return_value: str | None) -> None: ...  # noqa: D102


@pytest.fixture
def mock_docker_bin(mocker: MockerFixture) -> MockDockerBinCallable:
    def _mock_docker_bin(*, return_value: str | None) -> None:
        mocker.patch(
            "ansible_toolbox.__main__.shutil.which",
            return_value=return_value,
        )
        importlib.reload(main)

    return _mock_docker_bin


@pytest.fixture
def mock_subprocess_run(mocker: MockerFixture) -> Mock:
    return mocker.patch("ansible_toolbox.__main__.subprocess.run")


def test_is_docker_image_present_docker_bin_is_none(
    mock_docker_bin: MockDockerBinCallable,
) -> None:
    mock_docker_bin(return_value=None)

    with pytest.raises(AssertionError):
        main.is_docker_image_present()


def test_is_docker_image_present_success(
    mock_docker_bin: MockDockerBinCallable,
    mock_subprocess_run: Mock,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_subprocess_run.return_value = CompletedProcess("", 0)
    assert main.is_docker_image_present() is True


def test_is_docker_image_present_failed(
    mock_docker_bin: MockDockerBinCallable,
    mock_subprocess_run: Mock,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_subprocess_run.return_value = CompletedProcess("", 1)
    assert main.is_docker_image_present() is False


def test_build_docker_image_docker_bin_is_none(
    tmp_path: str,
    mock_docker_bin: MockDockerBinCallable,
) -> None:
    mock_docker_bin(return_value=None)
    with pytest.raises(AssertionError):
        main.build_docker_image(tmp_path)


def test_build_docker_image_success(
    tmp_path: str,
    mock_docker_bin: MockDockerBinCallable,
    mock_subprocess_run: Mock,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_subprocess_run.return_value = CompletedProcess("", 0)
    main.build_docker_image(tmp_path)


def test_build_docker_image_failed(
    tmp_path: str,
    mock_docker_bin: MockDockerBinCallable,
    mock_subprocess_run: Mock,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_subprocess_run.return_value = CompletedProcess("", 1)

    with pytest.raises(RuntimeError) as err:
        main.build_docker_image(tmp_path)

    assert "Failed to build Docker image" in str(err.value)


def test_get_dockerfile_success() -> None:
    dockerfile = main.get_dockerfile(
        ["some-package-1", "some-package-2"],
    )

    assert "some-package-1" in dockerfile
    assert "some-package-2" in dockerfile


def test_get_dockerfile_failed(mocker: MockerFixture) -> None:
    mock_subs = mocker.patch(
        "ansible_toolbox.__main__.CustomTemplate.substitute",
    )

    mock_subs.side_effect = [ValueError("something went wrong")]

    with pytest.raises(RuntimeError) as err:
        main.get_dockerfile(
            ["some-package-1", "some-package-2"],
        )

    assert "Failed to generate the Dockerfile" in str(err.value)


def test_ensure_docker_image_success(mocker: MockerFixture) -> None:
    dockerfile_content = "dockerfile content"

    mocker.patch(
        "ansible_toolbox.__main__.get_dockerfile",
        return_value=dockerfile_content,
    )

    mock_build_docker_image = mocker.patch(
        "ansible_toolbox.__main__.build_docker_image",
    )

    main.ensure_docker_image(["some-package-1", "some-package-2"])

    mock_build_docker_image.assert_called_once()


def test_execute_success(
    mock_docker_bin: MockDockerBinCallable,
    mocker: MockerFixture,
) -> None:
    mock_docker_bin(return_value="somepath")
    mock_execvp = mocker.patch(
        "ansible_toolbox.__main__.os.execvp",
    )

    args = ["ansible-playbook", "test.yaml"]

    main.execute(args)

    mock_execvp.assert_called_once_with(mock.ANY, args)


def test_execute_failed(mock_docker_bin: MockDockerBinCallable) -> None:
    mock_docker_bin(return_value=None)
    with pytest.raises(AssertionError):
        main.execute([])


def test_translate_path_success(
    tmp_path: str,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "ansible_toolbox.__main__.Path.cwd",
        return_value=Path(tmp_path),
    )

    assert main.translate_path(tmp_path) == "/workspace"


def test_translate_path_fail(
    tmp_path: str,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "ansible_toolbox.__main__.Path.cwd",
        return_value=Path("/home"),
    )

    with pytest.raises(ValueError) as err:  # noqa: PT011
        assert main.translate_path(tmp_path) == "/workspace"

    assert str(err.value) == (
        f"Path {tmp_path!s} is outside the current workspace and "
        "cannot be accessed in the container."
    )


def test_prepare_arguments_interative(
    mock_docker_bin: MockDockerBinCallable,
    mocker: MockerFixture,
) -> None:
    mock_docker_bin(return_value="/docker")
    arguments = ["some_command"]
    interactive = True
    extra_volumes = ["/path/to/volume1", "/path/to/volume2"]
    extra_envs = ["ENV1=value1", "ENV2=value2"]

    mocker.patch(
        "ansible_toolbox.__main__.Path.cwd",
        return_value="/mock/cwd",
    )

    result = main.prepare_arguments(
        arguments,
        interactive=interactive,
        extra_volumes=extra_volumes,
        extra_envs=extra_envs,
    )

    assert result[:3] == ["/docker", "run", "-it"]
    assert "--rm" in result
    assert "--name" in result
    assert result[result.index("--name") + 1] == "ansible-toolbox"
    assert "-v" in result and "/mock/cwd:/workspace:ro,z" in result  # noqa: PT018
    assert "-e" in result and "ENV1=value1" in result  # noqa: PT018
    assert "ENV2=value2" in result
    assert "ansible-toolbox:latest" in result
    assert "/bin/sh" in result


def test_prepare_arguments_non_interactive(
    tmp_path: Path,
    mock_docker_bin: MockDockerBinCallable,
    mocker: MockerFixture,
) -> None:
    mock_docker_bin(return_value="/docker")
    arguments = ["some_command", "/path/to/file"]
    interactive = False

    mocker.patch(
        "ansible_toolbox.__main__.Path.cwd",
        return_value=tmp_path,
    )

    result = main.prepare_arguments(
        arguments,
        interactive=interactive,
        extra_volumes=[],
        extra_envs=[],
    )

    assert result[:2] == ["/docker", "run"]
    assert "-it" not in result
    assert "-c" in result
    assert "cd /workspace" in result[result.index("-c") + 1]
    assert "some_command" in result[result.index("-c") + 1]
    assert "/path/to/file" in result[result.index("-c") + 1]


def test_prepare_arguments_no_dockerbin_fail(
    mock_docker_bin: MockDockerBinCallable,
) -> None:
    mock_docker_bin(return_value=None)

    with pytest.raises(AssertionError):
        main.prepare_arguments(
            ["some_command"],
            interactive=False,
            extra_volumes=[],
            extra_envs=[],
        )


def test_parse_arguments_no_args() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args([])
    expected = Namespace(
        help=False,
        command=[],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )
    assert args == expected


def test_parse_arguments_help() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args(["--at-help"])
    expected = Namespace(
        help=True,
        command=[],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )
    assert args == expected


def test_parse_arguments_command() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args(["ansible-playbook", "site.yml"])
    expected = Namespace(
        help=False,
        command=["ansible-playbook", "site.yml"],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )
    assert args == expected


def test_parse_arguments_interactive() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args(["--at-i"])
    expected = Namespace(
        help=False,
        command=[],
        interactive=True,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )
    assert args == expected


def test_parse_arguments_additional_python_packages() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args(
        [
            "--at-add-py-package",
            "package1",
            "--at-add-py-package",
            "package2",
        ],
    )
    expected = Namespace(
        help=False,
        command=[],
        interactive=False,
        additional_python_packages=["package1", "package2"],
        volumes=[],
        envs=[],
    )
    assert args == expected


def test_parse_arguments_volumes() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args(
        [
            "--at-volume",
            "/host:/container",
            "--at-volume",
            "/data:/data",
        ],
    )
    expected = Namespace(
        help=False,
        command=[],
        interactive=False,
        additional_python_packages=[],
        volumes=["/host:/container", "/data:/data"],
        envs=[],
    )
    assert args == expected


def test_parse_arguments_envs() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args(
        ["--at-env", "ENV_VAR=value", "--at-env", "DEBUG=1"],
    )
    expected = Namespace(
        help=False,
        command=[],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=["ENV_VAR=value", "DEBUG=1"],
    )
    assert args == expected


def test_parse_arguments_combined() -> None:
    parser = main.parse_arguments()
    args = parser.parse_args(
        [
            "--at-help",
            "--at-i",
            "--at-add-py-package",
            "package1",
            "--at-add-py-package",
            "package2",
            "--at-volume",
            "/host:/container",
            "--at-env",
            "ENV_VAR=value",
            "ansible-playbook",
            "site.yml",
        ],
    )
    expected = Namespace(
        help=True,
        command=["ansible-playbook", "site.yml"],
        interactive=True,
        additional_python_packages=["package1", "package2"],
        volumes=["/host:/container"],
        envs=["ENV_VAR=value"],
    )
    assert args == expected


def test_main_docker_bin_not_found(
    mock_docker_bin: MockDockerBinCallable,
) -> None:
    mock_docker_bin(return_value=None)

    with pytest.raises(RuntimeError) as err:
        main.main()

    assert "Docker is not installed or is not in $PATH" in str(err.value)


def test_main_help(
    mock_docker_bin: MockDockerBinCallable,
    mocker: MockerFixture,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_parser = mocker.MagicMock()
    mock_parser.parse_known_args.return_value = (
        mocker.MagicMock(help=True),
        [],
    )

    mocker.patch(
        "ansible_toolbox.__main__.parse_arguments",
        return_value=mock_parser,
    )

    main.main()
    mock_parser.print_help.assert_called_once()


def test_main_no_command(
    mock_docker_bin: MockDockerBinCallable,
    mocker: MockerFixture,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_parser = mocker.MagicMock()
    mock_parser.parse_known_args.return_value = (
        mocker.MagicMock(help=False),
        [],
    )
    mock_parser.parse_args.return_value = mocker.MagicMock(command=[])

    mocker.patch(
        "ansible_toolbox.__main__.parse_arguments",
        return_value=mock_parser,
    )

    with pytest.raises(ValueError) as err:  # noqa: PT011
        main.main()

    assert "Please provide the `command` to be executed" in str(err.value)


def test_main_docker_image_not_present(
    mock_docker_bin: MockDockerBinCallable,
    mocker: MockerFixture,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_parser = mocker.MagicMock()
    mock_args = mocker.MagicMock(
        help=False,
        command=["ansible-playbook", "site.yml"],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )
    mock_parser.parse_known_args.return_value = (
        mocker.MagicMock(help=False),
        [],
    )
    mock_parser.parse_args.return_value = mock_args

    mocker.patch(
        "ansible_toolbox.__main__.parse_arguments",
        return_value=mock_parser,
    )
    mock_is_image_present = mocker.patch(
        "ansible_toolbox.__main__.is_docker_image_present",
        return_value=False,
    )
    mock_ensure_image = mocker.patch(
        "ansible_toolbox.__main__.ensure_docker_image",
    )
    mock_prepare_args = mocker.patch(
        "ansible_toolbox.__main__.prepare_arguments",
        return_value=["docker", "run"],
    )
    mock_execute = mocker.patch(
        "ansible_toolbox.__main__.execute",
    )

    main.main()

    mock_is_image_present.assert_called_once()
    mock_ensure_image.assert_called_once_with(
        mock_args.additional_python_packages,
    )
    mock_prepare_args.assert_called_once_with(
        mock_args.command,
        interactive=mock_args.interactive,
        extra_volumes=mock_args.volumes,
        extra_envs=mock_args.envs,
    )
    mock_execute.assert_called_once_with(["docker", "run"])


def test_main_docker_image_present(
    mock_docker_bin: MockDockerBinCallable,
    mocker: MockerFixture,
) -> None:
    mock_docker_bin(return_value="/docker")
    mock_parser = mocker.MagicMock()
    mock_args = mocker.MagicMock(
        help=False,
        command=["ansible-playbook", "site.yml"],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )
    mock_parser.parse_known_args.return_value = (
        mocker.MagicMock(help=False),
        [],
    )
    mock_parser.parse_args.return_value = mock_args

    mocker.patch(
        "ansible_toolbox.__main__.parse_arguments",
        return_value=mock_parser,
    )
    mock_is_image_present = mocker.patch(
        "ansible_toolbox.__main__.is_docker_image_present",
        return_value=True,
    )
    mock_prepare_args = mocker.patch(
        "ansible_toolbox.__main__.prepare_arguments",
        return_value=["docker", "run"],
    )
    mock_execute = mocker.patch(
        "ansible_toolbox.__main__.execute",
    )

    main.main()

    mock_is_image_present.assert_called_once()
    mock_prepare_args.assert_called_once_with(
        mock_args.command,
        interactive=mock_args.interactive,
        extra_volumes=mock_args.volumes,
        extra_envs=mock_args.envs,
    )
    mock_execute.assert_called_once_with(["docker", "run"])
