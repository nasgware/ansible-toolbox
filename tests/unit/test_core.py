from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from ansible_toolbox.core import translate_path


def test_translate_path_success(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """Test successful path translation."""
    mocker.patch(
        "pathlib.Path.cwd",
        return_value=Path(tmp_path),
    )

    assert translate_path(str(tmp_path)) == "/workspace"


def test_translate_path_fail(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """Test failed path translation."""
    mocker.patch(
        "pathlib.Path.cwd",
        return_value=Path("/home"),
    )

    with pytest.raises(ValueError, match="outside the current workspace"):
        translate_path(str(tmp_path))
