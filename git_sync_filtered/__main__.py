#!/usr/bin/env python3
"""
git-sync-filtered - Sync filtered commits from private to public repo

Uses git-filter-repo and GitPython.

Usage:
    git-sync-filtered --private /path/to/private --public /path/to/public --keep src --keep docs
"""

import shutil
import tempfile
from itertools import filterfalse
from pathlib import Path
from typing import Optional

import click
import git
from git_filter_repo import FilteringOptions, RepoFilter


def read_paths_from_file(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text().splitlines())
    return list(filterfalse(lambda line: line.startswith("#") or not line, lines))


def collect_paths_to_keep(
    keep: tuple[str, ...], keep_from_file: Optional[str]
) -> list[str]:
    paths_to_keep = set(keep)

    if keep_from_file:
        paths_to_keep.update(read_paths_from_file(Path(keep_from_file)))

    return sorted(list(paths_to_keep))


def run_filter_repo(repo_path: Path, paths_to_keep: list[str]) -> None:
    import os

    old_cwd = os.getcwd()
    os.chdir(repo_path)

    try:
        argv = ["--force", "--partial"]
        for path in paths_to_keep:
            argv.extend(["--path", path])

        filter_args = FilteringOptions.parse_args(argv, error_on_empty=False)
        repo_filter = RepoFilter(filter_args)
        repo_filter.run()
    finally:
        os.chdir(old_cwd)


def push_to_remote(
    repo: git.Repo,
    public_url: str,
    sync_branch: str,
    private_branch: str,
    force: bool = False,
    dry_run: bool = False,
) -> list[str]:
    # Set up public remote
    if "public" not in repo.remotes:
        repo.create_remote("public", public_url)
    else:
        repo.remote("public").set_url(public_url)

    # Fetch from public
    repo.remote("public").fetch()

    # Push to sync branch
    if dry_run:
        commits = []
        for commit in repo.iter_commits(private_branch):
            commits.append(f"  {commit.hexsha[:8]} {commit.summary}")
        return commits
    else:
        refspec = f"refs/heads/{private_branch}:refs/heads/{sync_branch}"
        repo.remote("public").push(refspec=refspec, force=force)
        return []


@click.command()
@click.option("--private", required=True, help="Private repo path or URL")
@click.option("--public", required=True, help="Public repo path or URL")
@click.option("--keep", multiple=True, help="Paths to keep (can specify multiple)")
@click.option(
    "--keep-from-file",
    type=click.Path(exists=True),
    help="File containing paths to keep (one per line)",
)
@click.option("--sync-branch", default="upstream/sync", help="Sync branch name")
@click.option("--main-branch", default="main", help="Main branch name")
@click.option("--private-branch", default="main", help="Private branch to sync from")
@click.option(
    "--dry-run", is_flag=True, help="Show what would happen without making changes"
)
@click.option("--merge", is_flag=True, help="Merge into main branch after sync")
@click.option("--force", is_flag=True, help="Force push")
def main(
    private,
    public,
    keep,
    keep_from_file,
    sync_branch,
    main_branch,
    private_branch,
    dry_run,
    merge,
    force,
):
    """Sync filtered commits from private to public repository."""

    paths_to_keep = collect_paths_to_keep(keep, keep_from_file)

    if not paths_to_keep:
        raise click.ClickException(
            "At least one --keep path or --keep-from-file required"
        )

    click.echo("=== Git Filter Sync ===")
    click.echo(f"Private:    {private}")
    click.echo(f"Public:     {public}")
    click.echo(f"Keep:       {paths_to_keep}")
    click.echo(f"Sync to:    {sync_branch}")
    click.echo()

    # Create temp directory
    work_dir = Path(tempfile.mkdtemp(prefix="git-sync-"))
    click.echo(f"[git-sync] Working in: {work_dir}")

    try:
        # Clone private repo using GitPython
        private_clone = work_dir / "private"
        click.echo(f"[git-sync] Cloning private repo to {private_clone}...")
        private_repo = git.Repo.clone_from(private, str(private_clone))

        # Run filter-repo using the library
        click.echo("[git-sync] Running git-filter-repo...")
        run_filter_repo(private_clone, paths_to_keep)

        # Push to remote
        click.echo("[git-sync] Pushing to sync branch...")
        dry_run_commits = push_to_remote(
            private_repo, public, sync_branch, private_branch, force, dry_run
        )

        if dry_run:
            click.echo(f"[git-sync] DRY RUN - Would push to {sync_branch}")
            click.echo()
            click.echo("Commits that would be pushed:")
            for commit in dry_run_commits:
                click.echo(commit)
        else:
            click.echo()
            click.echo(f"=== Synced to {sync_branch} ===")

        if merge and not dry_run:
            click.echo(f"[git-sync] Merging into {main_branch}...")

            # Checkout main
            private_repo.heads[main_branch].checkout()

            try:
                # Merge sync branch into main
                sync_head = private_repo.heads[sync_branch]
                private_repo.index.merge_commit(
                    sync_head, msg=f"Merge branch '{sync_branch}'"
                )

                # Push merged result
                private_repo.remote("public").push(
                    refspec=f"refs/heads/{main_branch}:refs/heads/{main_branch}"
                )
                click.echo(f"[git-sync] Merged and pushed to {main_branch}")
            except git.GitCommandError:
                click.echo("[git-sync] Merge conflict! Please resolve manually:")
                click.echo(f"  cd {private_clone}")
                click.echo(f"  git checkout {main_branch}")
                click.echo(f"  git merge {sync_branch}")
                click.echo("  # Fix conflicts")
                click.echo(f"  git push public {main_branch}")

        click.echo()
        click.echo("Done!")

    finally:
        # Cleanup
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
