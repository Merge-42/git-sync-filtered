from unittest.mock import MagicMock

from git import Repo

from git_sync_filtered.verify import get_file_hashes, verify_sync_integrity


def _make_repo(*ls_tree_responses: str) -> MagicMock:
    """Create a mock Repo whose git.ls_tree returns the given responses in sequence."""
    repo = MagicMock(spec=Repo)
    repo.git.ls_tree.side_effect = list(ls_tree_responses)
    return repo


def test_verify_sync_integrity_returns_true_when_hashes_match() -> None:
    """When file hashes match between repos, verify returns True."""
    private = _make_repo("100644 blob abc1234 file1.py", "100644 blob def5678 file2.py")
    public = _make_repo("100644 blob abc1234 file1.py", "100644 blob def5678 file2.py")

    assert verify_sync_integrity(private, public, ["file1.py", "file2.py"]) is True


def test_verify_sync_integrity_returns_false_when_hashes_differ() -> None:
    """When file hashes differ between repos, verify returns False."""
    private = _make_repo("100644 blob abc1234 file1.py", "100644 blob def5678 file2.py")
    public = _make_repo("100644 blob abc1234 file1.py", "100644 blob WRONG456 file2.py")

    assert verify_sync_integrity(private, public, ["file1.py", "file2.py"]) is False


def test_verify_sync_integrity_handles_missing_file_in_public() -> None:
    """When a file exists in private but not public, verify returns False."""
    private = _make_repo("100644 blob abc1234 file1.py", "100644 blob def5678 file2.py")
    public = _make_repo("100644 blob abc1234 file1.py", "")  # file2.py absent

    assert verify_sync_integrity(private, public, ["file1.py", "file2.py"]) is False


def test_verify_sync_integrity_handles_extra_file_in_public() -> None:
    """When a file exists in public but not private, verify returns False."""
    private = _make_repo("100644 blob abc1234 file1.py", "")  # file2.py absent
    public = _make_repo("100644 blob abc1234 file1.py", "100644 blob def5678 file2.py")

    assert verify_sync_integrity(private, public, ["file1.py", "file2.py"]) is False


def test_verify_sync_integrity_empty_paths() -> None:
    """When no paths provided, verify returns True (nothing to compare)."""
    private = MagicMock(spec=Repo)
    public = MagicMock(spec=Repo)

    assert verify_sync_integrity(private, public, []) is True
    private.git.ls_tree.assert_not_called()
    public.git.ls_tree.assert_not_called()


def test_get_file_hashes_parses_ls_tree_output() -> None:
    """Verify get_file_hashes correctly parses git ls-tree output."""
    repo = _make_repo("100644 blob abc1234 file1.py", "100644 blob def5678 file2.py")

    hashes = get_file_hashes(repo, ["file1.py", "file2.py"])

    assert hashes == {"file1.py": "abc1234", "file2.py": "def5678"}


def test_get_file_hashes_handles_empty_output() -> None:
    """Verify get_file_hashes handles empty ls-tree output."""
    repo = _make_repo("")

    assert get_file_hashes(repo, ["nonexistent.py"]) == {}
