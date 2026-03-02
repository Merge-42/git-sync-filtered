from unittest.mock import MagicMock

import pytest
from git import Repo

from git_sync_filtered.lock import acquire_sync_lock, check_sync_lock, release_sync_lock


def test_check_sync_lock_returns_false_when_branch_does_not_exist(
    mock_repo: MagicMock,
) -> None:
    """When sync branch doesn't exist, check returns False (no lock)."""
    mock_repo.remote.return_value.refs = []

    result = check_sync_lock(mock_repo, "public", "upstream/sync")

    assert result is False


def test_check_sync_lock_returns_true_when_branch_exists(mock_repo: MagicMock) -> None:
    """When sync branch exists, check returns True (lock held)."""
    mock_ref = MagicMock()
    mock_ref.remote_head = "upstream/sync"
    mock_repo.remote.return_value.refs = [mock_ref]

    result = check_sync_lock(mock_repo, "public", "upstream/sync")

    assert result is True


def test_acquire_sync_lock_creates_branch(mock_repo: MagicMock) -> None:
    """Acquire lock should create the sync branch."""
    acquire_sync_lock(mock_repo, "public", "upstream/sync", "main")

    mock_repo.git.branch.assert_called_once_with("upstream/sync", "main")


def test_release_sync_lock_deletes_branch(mock_repo: MagicMock) -> None:
    """Release lock should delete the sync branch."""
    release_sync_lock(mock_repo, "public", "upstream/sync")

    mock_repo.git.branch.assert_called_once_with("-D", "upstream/sync")


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock(spec=Repo)
    repo.remote.return_value = MagicMock()
    return repo
