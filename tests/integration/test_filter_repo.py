import subprocess

from git_sync_filtered.sync import run_filter_repo


def test_run_filter_repo_filters_correctly(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    (repo_path / "src").mkdir()
    (repo_path / "src" / "main.py").write_text("print('hello')")
    (repo_path / "docs").mkdir()
    (repo_path / "docs" / "README.md").write_text("# Docs")
    (repo_path / "secrets").mkdir()
    (repo_path / "secrets" / "passwords.txt").write_text("passwords!")

    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo_path,
        check=True,
        env={
            **__import__("os").environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_COMMITTER_NAME": "Test",
        },
    )

    run_filter_repo(repo_path, ["src", "docs"])

    assert (repo_path / "src" / "main.py").exists()
    assert (repo_path / "docs" / "README.md").exists()
    assert not (repo_path / "secrets").exists()
