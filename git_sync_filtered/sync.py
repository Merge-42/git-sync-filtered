import os
from itertools import filterfalse
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, TypedDict

import git
from git_filter_repo import FilteringOptions, RepoFilter

from git_sync_filtered.lock import check_sync_lock
from git_sync_filtered.marker import (
    append_marker_to_commit,
    find_last_synced_sha,
    parse_marker,
)


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
    """Run git-filter-repo to filter repository to only keep specified paths."""
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

    if dry_run:
        return [
            f"  {c.hexsha[:8]} {c.summary}" for c in repo.iter_commits(private_branch)
        ]

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


def _decode_message(msg: str | bytes) -> str:
    return msg.decode("utf-8") if isinstance(msg, bytes) else msg


def _get_last_synced_sha_from_remote(
    repo: git.Repo, sync_branch: str, marker_prefix: str
) -> str | None:
    """Get the last synced private SHA from the public repo's sync branch commit markers."""
    try:
        messages = [
            _decode_message(c.message)
            for c in repo.iter_commits(f"public/{sync_branch}")
        ]
        return find_last_synced_sha(messages, marker_prefix)
    except Exception:
        return None


def _rewrite_commits_with_markers(
    repo: git.Repo, branch: str, marker_prefix: str
) -> None:
    """Rewrite commit messages to include sync markers for commits not yet marked.

    Processes oldest-to-newest so each amend applies cleanly in sequence.
    """
    commits = list(repo.iter_commits(branch))

    for commit in reversed(commits):
        message = _decode_message(commit.message)

        if parse_marker(message, marker_prefix):
            continue

        new_message = append_marker_to_commit(message, commit.hexsha, marker_prefix)

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

        # Step 1: Fetch public state to determine what was last synced
        last_synced_sha: str | None = None
        if not dry_run and not reset:
            probe_path = work_dir_path / "probe"
            probe_repo = git.Repo.clone_from(private, str(probe_path))
            probe_repo.create_remote("public", public)
            try:
                probe_repo.remote("public").fetch()
                last_synced_sha = _get_last_synced_sha_from_remote(
                    probe_repo, sync_branch, marker_prefix
                )
            except Exception:  # noqa: BLE001
                last_synced_sha = None

            lock_branch = f"{sync_branch}-in-progress"
            if check_sync_lock(probe_repo, "public", lock_branch):
                raise ValueError(
                    f"Sync already in progress: {lock_branch} branch exists"
                )

        # Step 2: Clone the private repo; apply graft for incremental sync
        private_clone = work_dir_path / "private"
        private_repo = git.Repo.clone_from(private, str(private_clone))

        with private_repo.config_writer() as config:
            config.set_value("user", "email", "git-sync-filtered@local")
            config.set_value("user", "name", "git-sync-filtered")

        if last_synced_sha:
            # Graft: treat last_synced_sha as a root so filter-repo only
            # rewrites commits after it
            try:
                private_repo.commit(last_synced_sha)
                grafts_file = private_clone / ".git" / "info" / "grafts"
                grafts_file.parent.mkdir(parents=True, exist_ok=True)
                grafts_file.write_text(f"{last_synced_sha}\n")
            except Exception:  # noqa: BLE001
                last_synced_sha = None  # SHA gone; fall back to full sync

        # Step 3: Filter the (possibly grafted) history
        run_filter_repo(str(private_clone), paths_to_keep)

        # Close and re-create Repo object after filter-repo rewrites history
        if hasattr(private_repo, "close"):
            try:
                private_repo.close()
            except OSError:  # nosec: B110
                pass

        private_repo = git.Repo(private_clone)

        with private_repo.config_writer() as config:
            config.set_value("user", "email", "git-sync-filtered@local")
            config.set_value("user", "name", "git-sync-filtered")

        if not dry_run:
            if "public" not in private_repo.remotes:
                private_repo.create_remote("public", public)
            else:
                private_repo.remote("public").set_url(public)

        # Step 4: Rewrite commit messages with sync markers
        _rewrite_commits_with_markers(private_repo, private_branch, marker_prefix)

        # Step 5: Push — force when incremental since SHAs are rewritten by filter-repo
        dry_run_commits = push_to_remote(
            private_repo,
            public,
            sync_branch,
            private_branch,
            force=True if last_synced_sha else force,
            dry_run=dry_run,
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
