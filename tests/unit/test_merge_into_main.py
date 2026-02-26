from unittest.mock import MagicMock

import pytest

from git_sync_filtered.__main__ import merge_into_main


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    mock_head = MagicMock()
    repo.heads = {"main": mock_head, "upstream/sync": MagicMock()}
    repo.remote.return_value = MagicMock()
    return repo


def test_merge_into_main_checkouts_main_branch(mock_repo):
    merge_into_main(repo=mock_repo, main_branch="main", sync_branch="upstream/sync")

    mock_repo.heads["main"].checkout.assert_called_once()


def test_merge_into_main_performs_merge(mock_repo):
    merge_into_main(repo=mock_repo, main_branch="main", sync_branch="upstream/sync")

    mock_repo.index.merge_commit.assert_called_once()


def test_merge_into_main_pushes_on_success(mock_repo):
    merge_into_main(repo=mock_repo, main_branch="main", sync_branch="upstream/sync")

    mock_repo.remote("public").push.assert_called_once()


def test_merge_into_main_returns_true_on_success(mock_repo):
    result = merge_into_main(
        repo=mock_repo, main_branch="main", sync_branch="upstream/sync"
    )

    assert result is True


def test_merge_into_main_returns_false_on_conflict(mock_repo):
    import git

    mock_repo.index.merge_commit.side_effect = git.GitCommandError("merge", 1)

    result = merge_into_main(
        repo=mock_repo, main_branch="main", sync_branch="upstream/sync"
    )

    assert result is False
    mock_repo.remote("public").push.assert_not_called()
