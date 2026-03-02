import git


def check_sync_lock(repo: git.Repo, remote_name: str, sync_branch: str) -> bool:
    """Check if sync is already in progress by checking if sync branch exists."""
    try:
        refs = repo.remote(remote_name).refs
        return sync_branch in [ref.name for ref in refs]
    except Exception:
        return False


def acquire_sync_lock(
    repo: git.Repo, remote_name: str, sync_branch: str, base_branch: str
) -> None:
    """Acquire lock by creating a sync branch from the base branch."""
    repo.git.branch(sync_branch, base_branch)


def release_sync_lock(repo: git.Repo, remote_name: str, sync_branch: str) -> None:
    """Release lock by deleting the sync branch."""
    repo.git.branch("-D", sync_branch)
