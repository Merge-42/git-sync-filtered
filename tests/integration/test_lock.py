import subprocess
from pathlib import Path

from git import Repo

from git_sync_filtered.lock import check_sync_lock


def run_git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env)


def test_check_sync_lock_integration(tmp_path: Path, git_env: dict[str, str]) -> None:
    """Check lock returns True when lock branch exists in public repo."""
    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=public_repo, check=True, env=git_env)

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    subprocess.run(["git", "init"], cwd=private_repo, check=True, env=git_env)

    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")
    run_git(private_repo, "add", ".", env=git_env)
    run_git(private_repo, "commit", "-m", "initial", env=git_env)

    # Get the current branch name (may be 'master' or 'main' depending on git config)
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=private_repo,
        capture_output=True,
        text=True,
        env=git_env,
    )
    current_branch = result.stdout.strip()

    run_git(private_repo, "remote", "add", "public", str(public_repo), env=git_env)
    run_git(
        private_repo,
        "push",
        "public",
        f"{current_branch}:upstream/sync-in-progress",
        env=git_env,
    )

    repo = Repo(str(private_repo))
    repo.remote("public").fetch()

    result = check_sync_lock(repo, "public", "upstream/sync-in-progress")

    assert result is True


def test_check_sync_lock_no_branch_integration(
    tmp_path: Path, git_env: dict[str, str]
) -> None:
    """Check lock returns False when lock branch doesn't exist."""
    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=public_repo, check=True, env=git_env)

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    subprocess.run(["git", "init"], cwd=private_repo, check=True, env=git_env)

    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")
    run_git(private_repo, "add", ".", env=git_env)
    run_git(private_repo, "commit", "-m", "initial", env=git_env)
    run_git(private_repo, "remote", "add", "public", str(public_repo), env=git_env)

    repo = Repo(str(private_repo))

    result = check_sync_lock(repo, "public", "upstream/sync")

    assert result is False
