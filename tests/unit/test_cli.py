from unittest import mock

import pytest
from pytest_mock import MockerFixture

from ansible_toolbox.__main__ import main, parse_arguments


def test_parse_arguments_no_command() -> None:
    """Test argument parsing with no command."""
    with pytest.raises(SystemExit):
        parse_arguments([])


def test_parse_arguments_help() -> None:
    """Test argument parsing with help flag."""
    with pytest.raises(SystemExit):
        parse_arguments(["--at-help"])


def test_parse_arguments_command() -> None:
    """Test argument parsing with command."""
    args = parse_arguments(["ansible-playbook", "site.yml"])
    assert args.command == ["ansible-playbook", "site.yml"]
    assert not args.interactive
    assert not args.additional_python_packages
    assert not args.volumes
    assert not args.envs


def test_parse_arguments_all_options() -> None:
    """Test argument parsing with all options."""

    # fmt: off
    args = parse_arguments(
        [
            "--at-i",
            "--at-add-py-package", "package1",
            "--at-add-py-package", "package2",
            "--at-volume", "/host:/container",
            "--at-env", "ENV_VAR=value",
            "ansible-playbook",
            "site.yml",
        ]
    )
    # fmt: on

    assert args.command == ["ansible-playbook", "site.yml"]
    assert args.interactive
    assert args.additional_python_packages == ["package1", "package2"]
    assert args.volumes == ["/host:/container"]
    assert args.envs == ["ENV_VAR=value"]


def test_main_success(mocker: MockerFixture) -> None:
    """Test successful main execution."""
    mock_args = mock.MagicMock(
        command=["ansible-playbook", "site.yml"],
        interactive=False,
        additional_python_packages=[],
        volumes=[],
        envs=[],
    )

    mock_toolbox = mock.MagicMock()

    mock_toolbox_class = mocker.patch(
        "ansible_toolbox.__main__.AnsibleToolbox",
        return_value=mock_toolbox,
    )

    mocker.patch(
        "ansible_toolbox.__main__.parse_arguments",
        return_value=mock_args,
    )

    main()

    mock_toolbox_class.assert_called_once()
    mock_toolbox.run.assert_called_once_with(mock_args)


def test_main_error(mocker: MockerFixture) -> None:
    """Test main execution with error."""
    mocker.patch(
        "ansible_toolbox.__main__.parse_arguments",
        side_effect=RuntimeError("Test error"),
    )

    mock_logger = mocker.patch("ansible_toolbox.__main__.logger")

    with pytest.raises(SystemExit) as err:
        main()

    assert err.value.code == 1

    mock_logger.exception.assert_called_once_with(
        "An unexpected error occurred: %s",
        "Test error",
    )
