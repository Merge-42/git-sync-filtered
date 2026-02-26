from unittest.mock import MagicMock

import pytest

from git_sync_filtered.sync import push_to_remote


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.remotes = []
    mock_remote = MagicMock()
    repo.create_remote.return_value = mock_remote
    repo.remote.return_value = mock_remote
    return repo


def test_push_to_remote_creates_remote_when_not_exists(mock_repo):
    mock_repo.remotes = []

    push_to_remote(
        repo=mock_repo,
        public_url="https://github.com/user/public.git",
        sync_branch="upstream/sync",
        private_branch="main",
    )

    mock_repo.create_remote.assert_called_once_with(
        "public", "https://github.com/user/public.git"
    )
    mock_repo.remote("public").fetch.assert_called_once()
    mock_repo.remote("public").push.assert_called_once()


def test_push_to_remote_updates_url_when_exists(mock_repo):
    mock_repo.remotes = ["public"]

    push_to_remote(
        repo=mock_repo,
        public_url="https://github.com/user/public.git",
        sync_branch="upstream/sync",
        private_branch="main",
    )

    mock_repo.remote("public").set_url.assert_called_once_with(
        "https://github.com/user/public.git"
    )
    mock_repo.create_remote.assert_not_called()


def test_push_to_remote_dry_run_returns_commits(mock_repo):
    mock_commit = MagicMock()
    mock_commit.hexsha = "abc123def"
    mock_commit.summary = "Initial commit"
    mock_repo.iter_commits.return_value = [mock_commit]

    result = push_to_remote(
        repo=mock_repo,
        public_url="https://github.com/user/public.git",
        sync_branch="upstream/sync",
        private_branch="main",
        dry_run=True,
    )

    assert result == ["  abc123de Initial commit"]
    mock_repo.remote("public").push.assert_not_called()


def test_push_to_remote_uses_force(mock_repo):
    push_to_remote(
        repo=mock_repo,
        public_url="https://github.com/user/public.git",
        sync_branch="upstream/sync",
        private_branch="main",
        force=True,
    )

    call_kwargs = mock_repo.remote("public").push.call_args[1]
    assert call_kwargs["force"] is True


def test_push_to_remote_builds_correct_refspec(mock_repo):
    push_to_remote(
        repo=mock_repo,
        public_url="https://github.com/user/public.git",
        sync_branch="upstream/sync",
        private_branch="feature branch",
    )

    call_args = mock_repo.remote("public").push.call_args[1]
    assert call_args["refspec"] == "refs/heads/feature branch:refs/heads/upstream/sync"
