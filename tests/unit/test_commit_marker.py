from git_sync_filtered.sync import (
    append_marker_to_commit,
    find_last_synced_sha,
    parse_marker,
)


def test_find_last_synced_sha_returns_sha_when_marker_found() -> None:
    """When commit message contains marker, return the SHA."""
    commit_messages = [
        "Add feature\n\n[synced: abc123def456]",
        "Fix bug",
        "Initial commit",
    ]

    result = find_last_synced_sha(commit_messages, "synced")

    assert result == "abc123def456"


def test_find_last_synced_sha_returns_none_when_no_marker() -> None:
    """When no commit has marker, return None."""
    commit_messages = [
        "Add feature",
        "Fix bug",
        "Initial commit",
    ]

    result = find_last_synced_sha(commit_messages, "synced")

    assert result is None


def test_find_last_synced_sha_returns_none_for_empty_list() -> None:
    """When commit list is empty, return None."""
    result = find_last_synced_sha([], "synced")

    assert result is None


def test_find_last_synced_sha_uses_custom_prefix() -> None:
    """When custom prefix is used, find marker with that prefix."""
    commit_messages = [
        "Add feature\n\n[custom: sha987654321]",
        "Fix bug",
    ]

    result = find_last_synced_sha(commit_messages, "custom")

    assert result == "sha987654321"


def test_find_last_synced_sha_returns_first_marker() -> None:
    """When multiple markers exist, return the first one found (most recent)."""
    commit_messages = [
        "New feature\n\n[synced: zyx987]",
        "Old feature\n\n[synced: abc123]",
    ]

    result = find_last_synced_sha(commit_messages, "synced")

    assert result == "zyx987"


def test_parse_marker_extracts_sha() -> None:
    """Parse marker should extract SHA from commit message."""
    message = "Add feature\n\n[synced: abc123def456]"

    result = parse_marker(message, "synced")

    assert result == "abc123def456"


def test_parse_marker_returns_none_when_no_marker() -> None:
    """Parse marker returns None when no marker in message."""
    message = "Add feature"

    result = parse_marker(message, "synced")

    assert result is None


def test_append_marker_to_commit_appends_marker() -> None:
    """Append marker should add marker to end of commit message."""
    message = "Add new feature"
    sha = "abc123def456"

    result = append_marker_to_commit(message, sha, "synced")

    assert result == "Add new feature\n\n[synced: abc123def456]"


def test_append_marker_to_commit_handles_existing_newline() -> None:
    """Append marker should handle message that already ends with newline."""
    message = "Add new feature\n"
    sha = "abc123def456"

    result = append_marker_to_commit(message, sha, "synced")

    assert result == "Add new feature\n\n[synced: abc123def456]"


def test_append_marker_to_commit_handles_multiline() -> None:
    """Append marker should work with multiline commit messages."""
    message = "Add new feature\n\nThis is a longer description"
    sha = "abc123def456"

    result = append_marker_to_commit(message, sha, "synced")

    assert "[synced: abc123def456]" in result
    assert result.endswith("abc123def456]")


def test_append_marker_to_commit_handles_existing_marker() -> None:
    """When marker already exists, it should be replaced."""
    message = "Add feature\n\n[synced: oldsha123]"
    sha = "newsha456"

    result = append_marker_to_commit(message, sha, "synced")

    assert result == "Add feature\n\n[synced: newsha456]"
    assert "oldsha123" not in result
