import os
from itertools import filterfalse
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, TypedDict

import git
from git_filter_repo import FilteringOptions, RepoFilter

from git_sync_filtered.lock import check_sync_lock
from git_sync_filtered.marker import find_last_synced_sha, parse_marker


class SyncResult(TypedDict):
    paths_to_keep: list[str]
    dry_run_commits: list[str]
    merge_success: bool | None
    last_synced_sha: str | None


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


def merge_into_main(repo: git.Repo, main_branch: str, sync_branch: str) -> bool:
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


def _get_last_synced_sha(repo: git.Repo, branch: str, marker_prefix: str) -> str | None:
    """Get the last synced SHA from commit messages in the branch."""
    try:
        commits = list(repo.iter_commits(branch))
        messages = []
        for commit in commits:
            msg = commit.message
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8")
            messages.append(msg)
        return find_last_synced_sha(messages, marker_prefix)
    except Exception:
        return None


def _rewrite_commits_with_markers(
    repo: git.Repo, branch: str, marker_prefix: str
) -> None:
    """Rewrite commit messages to include sync markers."""
    for commit in repo.iter_commits(branch):
        message = commit.message
        if isinstance(message, bytes):
            message = message.decode("utf-8")

        if parse_marker(message, marker_prefix):
            continue

        sha = commit.hexsha
        new_message = f"{message.rstrip()}\n\n[{marker_prefix}: {sha}]"

        try:
            repo.git.commit(message=new_message, amend=True)
        except git.GitCommandError:
            pass


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
    marker_prefix: str = "synced",
    reset: bool = False,
) -> SyncResult:
    paths_to_keep = collect_paths_to_keep(keep, keep_from_file)

    if not paths_to_keep:
        raise ValueError("At least one --keep path or --keep-from-file required")

    with TemporaryDirectory(prefix="git-sync-") as work_dir:
        work_dir_path = Path(work_dir)
        private_clone = work_dir_path / "private"
        private_repo = git.Repo.clone_from(private, str(private_clone))

        if not dry_run:
            if "public" not in private_repo.remotes:
                private_repo.create_remote("public", public)
            else:
                private_repo.remote("public").set_url(public)
            private_repo.remote("public").fetch()

            if check_sync_lock(private_repo, "public", sync_branch):
                raise ValueError(
                    f"Sync already in progress: {sync_branch} branch exists"
                )

        if not reset:
            _get_last_synced_sha(private_repo, private_branch, marker_prefix)

        run_filter_repo(str(private_clone), paths_to_keep)

        _rewrite_commits_with_markers(private_repo, private_branch, marker_prefix)

        dry_run_commits = push_to_remote(
            private_repo, public, sync_branch, private_branch, force, dry_run
        )

        final_synced_sha = _get_last_synced_sha(
            private_repo, private_branch, marker_prefix
        )

        if merge and not dry_run:
            success = merge_into_main(private_repo, main_branch, sync_branch)
            return {
                "paths_to_keep": paths_to_keep,
                "dry_run_commits": dry_run_commits,
                "merge_success": success,
                "last_synced_sha": final_synced_sha,
            }

        return {
            "paths_to_keep": paths_to_keep,
            "dry_run_commits": dry_run_commits,
            "merge_success": None,
            "last_synced_sha": final_synced_sha,
        }
