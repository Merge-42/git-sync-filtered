import os
import re
from itertools import filterfalse
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, TypedDict

import git
from git_filter_repo import FilteringOptions, RepoFilter


class SyncResult(TypedDict):
    paths_to_keep: list[str]
    dry_run_commits: list[str]
    merge_success: bool | None


def read_paths_from_file(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text().splitlines())
    return list(filterfalse(lambda line: line.startswith("#") or not line, lines))


def collect_paths_to_keep(
    keep: tuple[str, ...], keep_from_file: Optional[Path]
) -> list[str]:
    paths_to_keep: set[str] = set(keep)

    if keep_from_file:
        paths_to_keep.update(read_paths_from_file(keep_from_file))

    return sorted(paths_to_keep)


def run_filter_repo(repo_path: Path | str, paths_to_keep: list[str]) -> None:
    old_cwd = os.getcwd()
    os.chdir(repo_path)

    try:
        argv = ["--force", "--partial"]
        for path in paths_to_keep:
            argv.extend(["--path", path])

        filter_args = FilteringOptions.parse_args(argv, error_on_empty=False)
        repo_filter = RepoFilter(filter_args)
        repo_filter.run()
    finally:
        os.chdir(old_cwd)


def get_file_hashes(repo: git.Repo, paths: list[str]) -> dict[str, str]:
    """Get SHA-1 object hashes for files using git ls-tree."""
    hashes: dict[str, str] = {}
    for path in paths:
        result = repo.git.ls_tree("-r", "HEAD", "--", path)
        if not result:
            continue
        for line in result.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                obj_hash = parts[2]
                file_path = parts[3]
                hashes[file_path] = obj_hash
    return hashes


def verify_sync_integrity(
    private_repo: git.Repo,
    public_repo: git.Repo,
    paths_to_keep: list[str],
) -> bool:
    """
    Verify that synced files in public repo match filtered files from private repo.

    Compares file object hashes between private (filtered) and public repos.
    Returns True if hashes match, False otherwise.
    """
    if not paths_to_keep:
        return True

    private_hashes = get_file_hashes(private_repo, paths_to_keep)
    public_hashes = get_file_hashes(public_repo, paths_to_keep)

    return private_hashes == public_hashes


def parse_marker(message: str, prefix: str) -> str | None:
    """Extract SHA from commit message marker. Returns None if no marker found."""
    import re

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


def push_to_remote(
    repo: git.Repo,
    public_url: str,
    sync_branch: str,
    private_branch: str,
    force: bool = False,
    dry_run: bool = False,
) -> list[str]:
    if "public" not in repo.remotes:
        repo.create_remote("public", public_url)
    else:
        repo.remote("public").set_url(public_url)

    repo.remote("public").fetch()

    if dry_run:
        commits = []
        for commit in repo.iter_commits(private_branch):
            commits.append(f"  {commit.hexsha[:8]} {commit.summary}")
        return commits
    else:
        refspec = f"refs/heads/{private_branch}:refs/heads/{sync_branch}"
        repo.remote("public").push(refspec=refspec, force=force)
        return []


def merge_into_main(
    repo: git.Repo,
    main_branch: str,
    sync_branch: str,
) -> bool:
    repo.heads[main_branch].checkout()

    try:
        sync_head = repo.heads[sync_branch]
        repo.index.merge_commit(sync_head, msg=f"Merge branch '{sync_branch}'")

        repo.remote("public").push(
            refspec=f"refs/heads/{main_branch}:refs/heads/{main_branch}"
        )
        return True
    except git.GitCommandError:
        return False


def check_sync_lock(repo: git.Repo, remote_name: str, sync_branch: str) -> bool:
    """Check if sync is already in progress by checking if sync branch exists."""
    try:
        refs = repo.remote(remote_name).refs
        return sync_branch in [ref.name for ref in refs]
    except Exception:
        return False


def acquire_sync_lock(
    repo: git.Repo, remote_name: str, sync_branch: str, base_branch: str
) -> None:
    """Acquire lock by creating a sync branch from the base branch."""
    repo.git.branch(sync_branch, base_branch)


def release_sync_lock(repo: git.Repo, remote_name: str, sync_branch: str) -> None:
    """Release lock by deleting the sync branch."""
    repo.git.branch("-D", sync_branch)


def sync(
    private: str,
    public: str,
    keep: tuple[str, ...],
    keep_from_file: Optional[Path],
    sync_branch: str,
    main_branch: str,
    private_branch: str,
    dry_run: bool,
    merge: bool,
    force: bool,
) -> SyncResult:
    paths_to_keep = collect_paths_to_keep(keep, keep_from_file)

    if not paths_to_keep:
        raise ValueError("At least one --keep path or --keep-from-file required")

    with TemporaryDirectory(prefix="git-sync-") as work_dir:
        work_dir_path = Path(work_dir)
        private_clone = work_dir_path / "private"
        private_repo = git.Repo.clone_from(private, str(private_clone))

        run_filter_repo(str(private_clone), paths_to_keep)

        dry_run_commits = push_to_remote(
            private_repo, public, sync_branch, private_branch, force, dry_run
        )

        if merge and not dry_run:
            success = merge_into_main(private_repo, main_branch, sync_branch)
            return {
                "paths_to_keep": paths_to_keep,
                "dry_run_commits": dry_run_commits,
                "merge_success": success,
            }

        return {
            "paths_to_keep": paths_to_keep,
            "dry_run_commits": dry_run_commits,
            "merge_success": None,
        }
