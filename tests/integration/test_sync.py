import os
import subprocess
from pathlib import Path


def run_git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env)


def test_sync_full_flow(tmp_path: Path) -> None:
    """Integration test for sync function."""
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
    (private_repo / "docs").mkdir()
    (private_repo / "docs" / "README.md").write_text("# Docs")
    (private_repo / "secrets").mkdir()
    (private_repo / "secrets" / "password.txt").write_text("password!")

    run_git(private_repo, "init", env=env)
    run_git(private_repo, "checkout", "-b", "main", env=env)
    run_git(private_repo, "add", ".", env=env)
    run_git(private_repo, "commit", "-m", "initial", env=env)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    run_git(public_repo, "init", "--bare", env=env)

    from git_sync_filtered.sync import sync

    result = sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src", "docs"),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=False,
        merge=False,
        force=False,
    )

    assert result["paths_to_keep"] == ["docs", "src"]
    assert result["dry_run_commits"] == []
    assert result["merge_success"] is None

    cloned = tmp_path / "check_public"
    subprocess.run(
        ["git", "clone", str(public_repo), str(cloned)],
        check=True,
        env=env,
    )
    run_git(cloned, "checkout", "upstream/sync", env=env)

    assert (cloned / "src" / "main.py").exists()
    assert (cloned / "docs" / "README.md").exists()
    assert not (cloned / "secrets").exists()


def test_sync_dry_run(tmp_path: Path) -> None:
    """Integration test for sync function with dry_run=True."""
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

    result = sync(
        private=str(private_repo),
        public=str(public_repo),
        keep=("src",),
        keep_from_file=None,
        sync_branch="upstream/sync",
        main_branch="main",
        private_branch="main",
        dry_run=True,
        merge=False,
        force=False,
    )

    assert result["paths_to_keep"] == ["src"]
    assert len(result["dry_run_commits"]) == 1
    assert "initial" in result["dry_run_commits"][0]

    cloned = tmp_path / "check_public"
    subprocess.run(
        ["git", "clone", str(public_repo), str(cloned)],
        check=True,
        env=env,
        capture_output=True,
    )

    assert not (cloned / "src").exists()


def test_sync_requires_keep_paths(tmp_path: Path) -> None:
    """Integration test that sync raises error when no paths provided."""
    private_repo = tmp_path / "private_source"
    private_repo.mkdir()

    subprocess.run(["git", "init"], cwd=private_repo, check=True)

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=public_repo, check=True)

    from git_sync_filtered.sync import sync

    try:
        sync(
            private=str(private_repo),
            public=str(public_repo),
            keep=(),
            keep_from_file=None,
            sync_branch="upstream/sync",
            main_branch="main",
            private_branch="main",
            dry_run=False,
            merge=False,
            force=False,
        )
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "At least one --keep path" in str(e)
