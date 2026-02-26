from unittest.mock import MagicMock, patch

import pytest

from git_sync_filtered.__main__ import collect_paths_to_keep, run_filter_repo


@pytest.fixture
def mock_filter_repo():
    with (
        patch("git_sync_filtered.__main__.FilteringOptions") as mock_options,
        patch("git_sync_filtered.__main__.RepoFilter") as mock_filter,
    ):
        mock_filter_instance = MagicMock()
        mock_filter.return_value = mock_filter_instance
        yield mock_options, mock_filter_instance


def test_collect_paths_to_keep_from_args():
    result = collect_paths_to_keep(keep=("src", "docs"), keep_from_file=None)
    assert result == ["docs", "src"]


def test_collect_paths_to_keep_combines_args_and_file(tmp_path):
    file_path = tmp_path / "paths.txt"
    file_path.write_text("tests\nlib\n")

    result = collect_paths_to_keep(
        keep=("src",),
        keep_from_file=str(file_path),
    )

    assert result == ["lib", "src", "tests"]


def test_collect_paths_to_keep_removes_duplicates():
    result = collect_paths_to_keep(keep=("src", "docs", "src"), keep_from_file=None)

    assert result == ["docs", "src"]


def test_collect_paths_to_keep_keeps_first_occurrence():
    result = collect_paths_to_keep(
        keep=("src", "docs", "src", "tests"),
        keep_from_file=None,
    )

    assert result == ["docs", "src", "tests"]


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
