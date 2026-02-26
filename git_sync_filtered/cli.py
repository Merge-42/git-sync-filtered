import click

from git_sync_filtered.sync import sync


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

    try:
        result = sync(
            private=private,
            public=public,
            keep=keep,
            keep_from_file=keep_from_file,
            sync_branch=sync_branch,
            main_branch=main_branch,
            private_branch=private_branch,
            dry_run=dry_run,
            merge=merge,
            force=force,
        )
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo("=== Git Filter Sync ===")
    click.echo(f"Private:    {private}")
    click.echo(f"Public:     {public}")
    click.echo(f"Keep:       {result['paths_to_keep']}")
    click.echo(f"Sync to:    {sync_branch}")
    click.echo()

    if dry_run:
        click.echo(f"[git-sync] DRY RUN - Would push to {sync_branch}")
        click.echo()
        click.echo("Commits that would be pushed:")
        for commit in result["dry_run_commits"]:
            click.echo(commit)
    else:
        click.echo()
        click.echo(f"=== Synced to {sync_branch} ===")

    if merge and not dry_run:
        if result["merge_success"]:
            click.echo(f"[git-sync] Merged and pushed to {main_branch}")
        else:
            click.echo("[git-sync] Merge conflict! Please resolve manually:")

    click.echo()
    click.echo("Done!")
