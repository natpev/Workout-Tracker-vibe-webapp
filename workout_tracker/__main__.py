# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Operator CLI invoked with python -m workout_tracker.

Click parses explicit paths and confirmation. init-storage creates only a new
external tree; migrate-storage upgrades a separate candidate; check-storage
uses storage.py's read-only validation. Explicit restore-backup performs confirmed candidate recovery; no command deploys.
"""

import json

import click

from .storage import StorageError, initialize_storage, inspect_storage


@click.group()
def main():
    """Provide first-install and read-only diagnostic commands, never deployment."""


@main.command("release-info")
def release_info():
    """Print machine-readable release targets without reading or creating storage.

    An updater runs this in the newly built image without a data mount, compares
    target_schema_version with separately verified installed storage, then asks
    the operator before any explicit candidate migration. No Flask app starts.
    """
    from . import APP_VERSION, TARGET_SCHEMA_VERSION
    click.echo(json.dumps({"app_version": APP_VERSION,
                           "target_schema_version": TARGET_SCHEMA_VERSION}))


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


@main.command("migrate-storage")
@click.option("--data-root", required=True, type=click.Path(path_type=str))
@click.option("--confirm-upgrade", is_flag=True)
@click.option("--target-version", type=click.Choice(["2", "3", "4", "5"]), default="3", show_default=True)
def migrate(data_root, confirm_upgrade, target_version):
    """Copy and upgrade a known schema to the requested target, never the original."""
    from .migrations import migrate_storage
    if not confirm_upgrade:
        raise click.ClickException("Explicit --confirm-upgrade is required; no migration was performed.")
    try:
        details = migrate_storage(data_root, target_version=int(target_version))
    except StorageError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Schema {details['schema_version']} verified. " + ("New candidate activated; original preserved." if details["changed"] else "Already compatible; no copy or write performed."))


@main.command("list-backups")
@click.option("--data-root", required=True, type=click.Path(path_type=str))
def list_backups(data_root):
    """List server-controlled IDs when damaged storage prevents the web app from booting."""
    from .storage import storage_lock
    from .operations import read_state
    try:
        with storage_lock(data_root) as root:
            records=read_state(root)['backups']
        for row in sorted(records.values(),key=lambda row:row['created_at'],reverse=True):
            click.echo(f"{row['id']}  {row['created_at']}  schema {row['schema_version']}  {row['status']}")
    except StorageError as error:
        raise click.ClickException(str(error)) from error


@main.command("restore-backup")
@click.option("--data-root", required=True, type=click.Path(path_type=str))
@click.option("--backup-id", required=True)
@click.option("--operation-id", required=True, help="Fresh 32-digit lowercase hex token; reuse only to inspect the same attempt.")
@click.option("--confirm-restore", is_flag=True)
def restore_backup(data_root, backup_id, operation_id, confirm_restore):
    """Explicit offline recovery uses the identical candidate/identity/rollback safeguards."""
    from .maintenance import restore
    if not confirm_restore:
        raise click.ClickException('Explicit --confirm-restore is required. Later workouts are not merged automatically.')
    try:
        result=restore(data_root,backup_id,operation_id,True)
    except StorageError as error:
        raise click.ClickException(str(error)) from error
    if result['status']!='succeeded':
        raise click.ClickException('Restore not successful; inspect retained sources, operation audit and protected logs.')
    click.echo('Verified restore candidate selected. Original database and backup preserved. Restart workers and reload forms.')


@main.command("scheduler")
@click.option("--data-root", envvar="WORKOUT_DATA_ROOT", required=True, type=click.Path(path_type=str))
@click.option("--once", is_flag=True, help="Perform one due-check for diagnostics/tests, then exit.")
def scheduler_command(data_root, once):
    """Run the dedicated scheduler; missing settings remain disabled without initialization."""
    from .scheduler import run, tick
    try:
        if once: tick(data_root)
        else: run(data_root)
    except StorageError as error:
        raise click.ClickException(str(error)) from error


if __name__ == "__main__":
    main()
