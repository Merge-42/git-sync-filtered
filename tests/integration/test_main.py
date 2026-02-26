import os
import subprocess


def run_git(cwd, *args, env=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env)


def test_full_sync_flow(tmp_path):
    """Integration test covering the full main() flow."""
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

    from click.testing import CliRunner

    from git_sync_filtered.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--private",
            str(private_repo),
            "--public",
            str(public_repo),
            "--keep",
            "src",
            "--keep",
            "docs",
        ],
    )

    assert result.exit_code == 0, result.output

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


def test_dry_run(tmp_path):
    """Integration test for dry-run mode."""
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

    from click.testing import CliRunner

    from git_sync_filtered.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--private",
            str(private_repo),
            "--public",
            str(public_repo),
            "--keep",
            "src",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output
    assert "Commits that would be pushed" in result.output
