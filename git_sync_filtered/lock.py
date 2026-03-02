import git


def check_sync_lock(repo: git.Repo, remote_name: str, sync_branch: str) -> bool:
    """Check if sync is already in progress by checking if sync branch exists in remote.

    Assumes the caller has already fetched the remote. Uses remote_head attribute
    to match just the branch name (not the full 'remote/branch' ref name).
    """
    try:
        refs = repo.remote(remote_name).refs
        return sync_branch in [ref.remote_head for ref in refs]
    except Exception:
        return False
