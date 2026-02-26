import os
import subprocess


def test_full_sync_flow(tmp_path):
    """Integration test covering the full main() flow."""
    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")
    (private_repo / "docs").mkdir()
    (private_repo / "docs" / "README.md").write_text("# Docs")
    (private_repo / "secrets").mkdir()
    (private_repo / "secrets" / "password.txt").write_text("password!")

    subprocess.run(["git", "init"], cwd=private_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=private_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=private_repo,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
        },
    )

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=public_repo, check=True)

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
    subprocess.run(["git", "clone", str(public_repo), str(cloned)], check=True)
    subprocess.run(["git", "checkout", "upstream/sync"], cwd=cloned, check=True)

    assert (cloned / "src" / "main.py").exists()
    assert (cloned / "docs" / "README.md").exists()
    assert not (cloned / "secrets").exists()


def test_dry_run(tmp_path, capsys):
    """Integration test for dry-run mode."""
    private_repo = tmp_path / "private_source"
    private_repo.mkdir()
    (private_repo / "src").mkdir()
    (private_repo / "src" / "main.py").write_text("print('hello')")

    subprocess.run(["git", "init"], cwd=private_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=private_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=private_repo,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
        },
    )

    public_repo = tmp_path / "public_repo"
    public_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=public_repo, check=True)

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
