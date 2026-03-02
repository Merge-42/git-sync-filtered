from unittest.mock import MagicMock

import pytest
from git import Repo

from git_sync_filtered.lock import check_sync_lock


def test_check_sync_lock_returns_false_when_no_refs(mock_repo: MagicMock) -> None:
    """When remote has no refs, check returns False (no lock)."""
    mock_repo.remote.return_value.refs = []

    result = check_sync_lock(mock_repo, "public", "upstream/sync")

    assert result is False


def test_check_sync_lock_returns_true_when_lock_branch_exists(
    mock_repo: MagicMock,
) -> None:
    """When lock branch exists, check returns True (lock held)."""
    mock_ref = MagicMock()
    mock_ref.remote_head = "upstream/sync-in-progress"
    mock_repo.remote.return_value.refs = [mock_ref]

    result = check_sync_lock(mock_repo, "public", "upstream/sync-in-progress")

    assert result is True


def test_check_sync_lock_returns_false_when_only_dest_branch_exists(
    mock_repo: MagicMock,
) -> None:
    """Destination branch existing does not count as a lock."""
    mock_ref = MagicMock()
    mock_ref.remote_head = "upstream/sync"
    mock_repo.remote.return_value.refs = [mock_ref]

    result = check_sync_lock(mock_repo, "public", "upstream/sync-in-progress")

    assert result is False


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock(spec=Repo)
    repo.remote.return_value = MagicMock()
    return repo
