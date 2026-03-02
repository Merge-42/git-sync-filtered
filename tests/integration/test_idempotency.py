import os
import subprocess
from pathlib import Path


def run_git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env)


def test_marker_in_commit_message(tmp_path: Path) -> None:
    """Verify marker is appended to commit messages after sync."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")

    run_git(private_repo, "init", env=env)
    run_git(private_repo, "checkout", "-b", "main", env=env)
    run_git(private_repo, "add", ".", env=env)
    run_git(private_repo, "commit", "-m", "initial", env=env)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    run_git(public_repo, "init", "--bare", env=env)

    from git_sync_filtered.sync import sync

    sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
        marker_prefix="synced",
        reset=False,
    )

    cloned = tmp_path / "check_public"
    subprocess.run(
        ["git", "clone", str(public_repo), str(cloned)],
        check=True,
        env=env,
    )
    run_git(cloned, "checkout", "upstream/sync", env=env)

    result = subprocess.run(
        ["git", "log", "--format=%B", "-1"],
        cwd=cloned,
        capture_output=True,
        text=True,
        env=env,
    )
    commit_message = result.stdout.strip()

    assert "[synced:" in commit_message, f"Marker not found in commit: {commit_message}"


def test_idempotent_sync_no_duplicates(tmp_path: Path) -> None:
    """Running sync twice should not create duplicate commits."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")

    run_git(private_repo, "init", env=env)
    run_git(private_repo, "checkout", "-b", "main", env=env)
    run_git(private_repo, "add", ".", env=env)
    run_git(private_repo, "commit", "-m", "initial", env=env)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    run_git(public_repo, "init", "--bare", env=env)

    from git_sync_filtered.sync import sync

    sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
        marker_prefix="synced",
        reset=False,
    )

    sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
        marker_prefix="synced",
        reset=False,
    )

    cloned = tmp_path / "check_public"
    subprocess.run(
        ["git", "clone", str(public_repo), str(cloned)],
        check=True,
        env=env,
    )
    run_git(cloned, "checkout", "upstream/sync", env=env)

    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=cloned,
        capture_output=True,
        text=True,
        env=env,
    )
    commit_count = int(result.stdout.strip())

    assert commit_count == 1, f"Expected 1 commit, got {commit_count}"


def test_idempotent_sync_new_commits_only(tmp_path: Path) -> None:
    """Only new commits should be synced on subsequent runs."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")

    run_git(private_repo, "init", env=env)
    run_git(private_repo, "checkout", "-b", "main", env=env)
    run_git(private_repo, "add", ".", env=env)
    run_git(private_repo, "commit", "-m", "initial", env=env)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    run_git(public_repo, "init", "--bare", env=env)

    from git_sync_filtered.sync import sync

    sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
        marker_prefix="synced",
        reset=False,
    )

    (private_repo / "src" / "new.py").write_text("print('new')")
    run_git(private_repo, "add", ".", env=env)
    run_git(private_repo, "commit", "-m", "add new file", env=env)

    sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
        marker_prefix="synced",
        reset=False,
    )

    cloned = tmp_path / "check_public"
    subprocess.run(
        ["git", "clone", str(public_repo), str(cloned)],
        check=True,
        env=env,
    )
    run_git(cloned, "checkout", "upstream/sync", env=env)

    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=cloned,
        capture_output=True,
        text=True,
        env=env,
    )
    commit_count = int(result.stdout.strip())

    assert commit_count == 2, f"Expected 2 commits (initial + new), got {commit_count}"


def test_reset_sync_restarts_from_beginning(tmp_path: Path) -> None:
    """With reset flag, sync should re-sync all commits from beginning."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")

    run_git(private_repo, "init", env=env)
    run_git(private_repo, "checkout", "-b", "main", env=env)
    run_git(private_repo, "add", ".", env=env)
    run_git(private_repo, "commit", "-m", "initial", env=env)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    run_git(public_repo, "init", "--bare", env=env)

    from git_sync_filtered.sync import sync

    sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
        marker_prefix="synced",
        reset=False,
    )

    sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
        marker_prefix="synced",
        reset=True,
    )

    cloned = tmp_path / "check_public"
    subprocess.run(
        ["git", "clone", str(public_repo), str(cloned)],
        check=True,
        env=env,
    )
    run_git(cloned, "checkout", "upstream/sync", env=env)

    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=cloned,
        capture_output=True,
        text=True,
        env=env,
    )
    commit_count = int(result.stdout.strip())

    assert commit_count == 1, f"Expected 1 commit after reset, got {commit_count}"
