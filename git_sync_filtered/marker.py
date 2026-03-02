import re


def parse_marker(message: str, prefix: str) -> str | None:
    """Extract SHA from commit message marker. Returns None if no marker found."""
    pattern = rf"\[{prefix}:\s*([^\]]+)\]"
    match = re.search(pattern, message)
    if match:
        return match.group(1)
    return None


def append_marker_to_commit(message: str, sha: str, prefix: str) -> str:
    """Append or update marker in commit message."""
    marker = f"[{prefix}: {sha}]"
    pattern = rf"\[{prefix}:\s*[^\]]+\]"

    new_message = re.sub(pattern, "", message)
    new_message = new_message.rstrip()

    return f"{new_message}\n\n{marker}"


def find_last_synced_sha(commit_messages: list[str], prefix: str) -> str | None:
    """Find the SHA from the most recent commit with a sync marker."""
    for message in commit_messages:
        sha = parse_marker(message, prefix)
        if sha:
            return sha
    return None
