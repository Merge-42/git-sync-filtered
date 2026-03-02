from fnmatch import translate as glob_translate
from pathlib import Path

import click
from pydantic import BaseModel, ConfigDict, FilePath, field_validator, model_validator

from git_sync_filtered.sync import sync


class SyncConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    private: str
    public: str
    keep: tuple[str, ...]
    keep_from_file: FilePath | None = None
    sync_branch: str = "upstream/sync"
    main_branch: str = "main"
    private_branch: str = "main"
    dry_run: bool = False
    merge: bool = False
    force: bool = False

    @field_validator("keep", mode="after")
    @classmethod
    def validate_glob_paths(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for path in v:
            if not path:
                raise ValueError("Keep path cannot be empty")
            glob_translate(path)
        return v

    @model_validator(mode="after")
    def ensure_keep_paths(self) -> "SyncConfig":
        if not self.keep and not self.keep_from_file:
            raise ValueError("At least one --keep path or --keep-from-file required")
        return self

    @field_validator("sync_branch", "main_branch", "private_branch", mode="after")
    @classmethod
    def validate_branch_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Branch name cannot be empty")
        if v.startswith("/") or ".." in v:
            raise ValueError(f"Invalid branch name: {v!r}")
        return v


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
    private: str,
    public: str,
    keep: tuple[str, ...],
    keep_from_file: str | None,
    sync_branch: str,
    main_branch: str,
    private_branch: str,
    dry_run: bool,
    merge: bool,
    force: bool,
) -> None:
    """Sync filtered commits from private to public repository."""

    try:
        config = SyncConfig(
            private=private,
            public=public,
            keep=keep,
            keep_from_file=Path(keep_from_file) if keep_from_file else None,
            sync_branch=sync_branch,
            main_branch=main_branch,
            private_branch=private_branch,
            dry_run=dry_run,
            merge=merge,
            force=force,
        )
        result = sync(
            private=config.private,
            public=config.public,
            keep=config.keep,
            keep_from_file=config.keep_from_file,
            sync_branch=config.sync_branch,
            main_branch=config.main_branch,
            private_branch=config.private_branch,
            dry_run=config.dry_run,
            merge=config.merge,
            force=config.force,
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
