import os
import subprocess
from pathlib import Path


def run_git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env)


def test_verify_sync_integrity_success(tmp_path: Path) -> None:
    """Hash verification should pass when synced files match."""
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

    import git

    from git_sync_filtered.sync import sync
    from git_sync_filtered.verify import verify_sync_integrity

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

    private_git = git.Repo(str(private_repo))
    public_git = git.Repo(str(public_repo))

    result = verify_sync_integrity(
        private_git, public_git, ["src"], public_ref="upstream/sync"
    )

    assert result is True


def test_verify_sync_integrity_failure(tmp_path: Path) -> None:
    """Hash verification should fail when files don't match."""
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

    import git

    from git_sync_filtered.sync import sync
    from git_sync_filtered.verify import verify_sync_integrity

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

    (tmp_path / "public_checkout").mkdir()
    subprocess.run(
        ["git", "clone", str(public_repo), str(tmp_path / "public_checkout")],
        check=True,
        env=env,
    )
    checkout = tmp_path / "public_checkout"
    run_git(checkout, "checkout", "upstream/sync", env=env)
    (checkout / "src" / "main.py").write_text("print('modified')")
    run_git(checkout, "add", ".", env=env)
    run_git(checkout, "commit", "-m", "tamper", env=env)
    run_git(checkout, "push", "origin", "upstream/sync", env=env)

    private_git = git.Repo(str(private_repo))
    public_git = git.Repo(str(public_repo))

    result = verify_sync_integrity(
        private_git, public_git, ["src"], public_ref="upstream/sync"
    )

    assert result is False
