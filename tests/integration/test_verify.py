import subprocess
from pathlib import Path

import git

from git_sync_filtered.sync import sync
from git_sync_filtered.verify import verify_sync_integrity


def run_git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env)


def test_verify_sync_integrity_success(tmp_path: Path, git_env: dict[str, str]) -> None:
    """Hash verification should pass when synced files match."""
    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")

    run_git(private_repo, "init", env=git_env)
    run_git(private_repo, "checkout", "-b", "main", env=git_env)
    run_git(private_repo, "add", ".", env=git_env)
    run_git(private_repo, "commit", "-m", "initial", env=git_env)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    run_git(public_repo, "init", "--bare", env=git_env)

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
    )

    result = verify_sync_integrity(
        git.Repo(str(private_repo)),
        git.Repo(str(public_repo)),
        ["src"],
        public_ref="upstream/sync",
    )

    assert result is True


def test_verify_sync_integrity_failure(tmp_path: Path, git_env: dict[str, str]) -> None:
    """Hash verification should fail when public files have been tampered with."""
    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")

    run_git(private_repo, "init", env=git_env)
    run_git(private_repo, "checkout", "-b", "main", env=git_env)
    run_git(private_repo, "add", ".", env=git_env)
    run_git(private_repo, "commit", "-m", "initial", env=git_env)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    run_git(public_repo, "init", "--bare", env=git_env)

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
    )

    # Tamper with the public repo
    checkout = tmp_path / "public_checkout"
    checkout.mkdir()
    subprocess.run(
        ["git", "clone", str(public_repo), str(checkout)], check=True, env=git_env
    )
    run_git(checkout, "checkout", "upstream/sync", env=git_env)
    (checkout / "src" / "main.py").write_text("print('modified')")
    run_git(checkout, "add", ".", env=git_env)
    run_git(checkout, "commit", "-m", "tamper", env=git_env)
    run_git(checkout, "push", "origin", "upstream/sync", env=git_env)

    result = verify_sync_integrity(
        git.Repo(str(private_repo)),
        git.Repo(str(public_repo)),
        ["src"],
        public_ref="upstream/sync",
    )

    assert result is False
