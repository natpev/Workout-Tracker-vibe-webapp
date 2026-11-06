# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Operator CLI invoked with python -m workout_tracker.

Click parses explicit paths and confirmation. Only init-storage writes a new
external tree; check-storage uses storage.py's read-only validation.
"""

import click

from .storage import StorageError, initialize_storage, inspect_storage


@click.group()
def main():
    """Provide first-install and read-only diagnostic commands, never deployment."""


@main.command("init-storage")
@click.option("--data-root", required=True, type=click.Path(path_type=str))
@click.option("--confirm-new-storage", is_flag=True, help="Confirm a new, disposable or first-install tree.")
def init_storage(data_root, confirm_new_storage):
    """Initialize only a new path after explicit confirmation; preserve failures."""
    if not confirm_new_storage:
        raise click.ClickException("Explicit --confirm-new-storage is required; no storage was created.")
    try:
        initialize_storage(data_root)
    except StorageError as error:
        raise click.ClickException(str(error)) from error
    click.echo("New foundation storage initialized and verified. No workout tables exist yet.")


@main.command("check-storage")
@click.option("--data-root", required=True, type=click.Path(path_type=str))
def check_storage(data_root):
    """Verify external storage without initializing, repairing, or migrating it."""
    try:
        details = inspect_storage(data_root)
    except StorageError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Storage verified; schema version {details['schema_version']}.")


if __name__ == "__main__":
    main()
