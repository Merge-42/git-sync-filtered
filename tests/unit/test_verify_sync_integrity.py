from unittest.mock import MagicMock

import pytest
from git import Repo

from git_sync_filtered.verify import get_file_hashes, verify_sync_integrity


def test_verify_sync_integrity_returns_true_when_hashes_match(
    mock_repo: MagicMock,
) -> None:
    """When file hashes match between repos, verify returns True."""
    mock_repo.git.ls_tree.side_effect = [
        "100644 blob abc1234 file1.py",
        "100644 blob def5678 file2.py",
        "100644 blob abc1234 file1.py",
        "100644 blob def5678 file2.py",
    ]

    result = verify_sync_integrity(mock_repo, mock_repo, ["file1.py", "file2.py"])

    assert result is True


def test_verify_sync_integrity_returns_false_when_hashes_differ(
    mock_repo: MagicMock,
) -> None:
    """When file hashes differ between repos, verify returns False."""
    mock_repo.git.ls_tree.side_effect = [
        "100644 blob abc1234 file1.py",
        "100644 blob def5678 file2.py",
        "100644 blob abc1234 file1.py",
        "100644 blob WRONG456 file2.py",
    ]

    result = verify_sync_integrity(mock_repo, mock_repo, ["file1.py", "file2.py"])

    assert result is False


def test_verify_sync_integrity_handles_missing_file_in_public(
    mock_repo: MagicMock,
) -> None:
    """When a file exists in private but not public, verify returns False."""
    mock_repo.git.ls_tree.side_effect = [
        "100644 blob abc1234 file1.py",
        "100644 blob def5678 file2.py",
        "100644 blob abc1234 file1.py",
        "",
    ]

    result = verify_sync_integrity(mock_repo, mock_repo, ["file1.py", "file2.py"])

    assert result is False


def test_verify_sync_integrity_handles_extra_file_in_public(
    mock_repo: MagicMock,
) -> None:
    """When a file exists in public but not private, verify returns False."""
    mock_repo.git.ls_tree.side_effect = [
        "100644 blob abc1234 file1.py",
        "",
        "100644 blob abc1234 file1.py",
        "100644 blob def5678 file2.py",
    ]

    result = verify_sync_integrity(mock_repo, mock_repo, ["file1.py", "file2.py"])

    assert result is False


def test_verify_sync_integrity_empty_paths(mock_repo: MagicMock) -> None:
    """When no paths provided, verify returns True (nothing to compare)."""
    mock_repo.git.ls_tree.return_value = ""

    result = verify_sync_integrity(mock_repo, mock_repo, [])

    assert result is True


def test_get_file_hashes_parses_ls_tree_output(mock_repo: MagicMock) -> None:
    """Verify get_file_hashes correctly parses git ls-tree output."""
    mock_repo.git.ls_tree.side_effect = [
        "100644 blob abc1234 file1.py",
        "100644 blob def5678 file2.py",
    ]

    hashes = get_file_hashes(mock_repo, ["file1.py", "file2.py"])

    assert hashes == {
        "file1.py": "abc1234",
        "file2.py": "def5678",
    }


def test_get_file_hashes_handles_empty_output(mock_repo: MagicMock) -> None:
    """Verify get_file_hashes handles empty ls-tree output."""
    mock_repo.git.ls_tree.return_value = ""

    hashes = get_file_hashes(mock_repo, ["nonexistent.py"])

    assert hashes == {}


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock(spec=Repo)
    return repo
