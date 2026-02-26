from unittest.mock import MagicMock, patch

import pytest

from git_sync_filtered.sync import run_filter_repo


@pytest.fixture
def mock_filter_repo():
    with (
        patch("git_sync_filtered.sync.FilteringOptions") as mock_options,
        patch("git_sync_filtered.sync.RepoFilter") as mock_filter,
    ):
        mock_filter_instance = MagicMock()
        mock_filter.return_value = mock_filter_instance
        yield mock_options, mock_filter_instance


def test_run_filter_repo_restores_cwd(tmp_path, mock_filter_repo):
    import os

    original_cwd = os.getcwd()
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    run_filter_repo(repo_path, ["src"])

    assert os.getcwd() == original_cwd


def test_run_filter_repo_builds_correct_argv(tmp_path, mock_filter_repo):
    mock_options, mock_filter_instance = mock_filter_repo

    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    run_filter_repo(repo_path, ["src", "docs"])

    mock_options.parse_args.assert_called_once()
    call_args = mock_options.parse_args.call_args
    argv = call_args[0][0]

    assert "--force" in argv
    assert "--partial" in argv
    assert "--path" in argv
    assert "src" in argv
    assert "docs" in argv
    mock_filter_instance.run.assert_called_once()
