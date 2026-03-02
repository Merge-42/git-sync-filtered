import git


def get_file_hashes(repo: git.Repo, paths: list[str]) -> dict[str, str]:
    """Get SHA-1 object hashes for files using git ls-tree."""
    hashes: dict[str, str] = {}
    for path in paths:
        result = repo.git.ls_tree("-r", "HEAD", "--", path)
        if not result:
            continue
        for line in result.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                obj_hash = parts[2]
                file_path = parts[3]
                hashes[file_path] = obj_hash
    return hashes


def verify_sync_integrity(
    private_repo: git.Repo,
    public_repo: git.Repo,
    paths_to_keep: list[str],
) -> bool:
    """
    Verify that synced files in public repo match filtered files from private repo.

    Compares file object hashes between private (filtered) and public repos.
    Returns True if hashes match, False otherwise.
    """
    if not paths_to_keep:
        return True

    private_hashes = get_file_hashes(private_repo, paths_to_keep)
    public_hashes = get_file_hashes(public_repo, paths_to_keep)

    return private_hashes == public_hashes
