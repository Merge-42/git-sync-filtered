import os
import subprocess
from pathlib import Path

from git import Repo

from git_sync_filtered.lock import check_sync_lock


def test_check_sync_lock_integration(tmp_path: Path) -> None:
    """Check lock returns True when sync branch exists in public repo."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=public_repo, check=True, env=env)

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    subprocess.run(["git", "init"], cwd=private_repo, check=True, env=env)

    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=private_repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=private_repo,
        check=True,
        env=env,
    )

    subprocess.run(
        ["git", "remote", "add", "public", str(public_repo)],
        cwd=private_repo,
        check=True,
        env=env,
    )
    subprocess.run(
        ["git", "push", "public", "main:upstream/sync-in-progress"],
        cwd=private_repo,
        check=True,
        env=env,
    )

    repo = Repo(str(private_repo))

    result = check_sync_lock(repo, "public", "upstream/sync-in-progress")

    assert result is True


def test_check_sync_lock_no_branch_integration(tmp_path: Path) -> None:
    """Check lock returns False when sync branch doesn't exist."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=public_repo, check=True, env=env)

    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    subprocess.run(["git", "init"], cwd=private_repo, check=True, env=env)

    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=private_repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=private_repo,
        check=True,
        env=env,
    )

    subprocess.run(
        ["git", "remote", "add", "public", str(public_repo)],
        cwd=private_repo,
        check=True,
        env=env,
    )

    repo = Repo(str(private_repo))

    result = check_sync_lock(repo, "public", "upstream/sync")

    assert result is False
