# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Explicit host service/emergency CLI; never invoked by application startup.

CLI operators can inspect/check or confirm an approved update. Browser users must
use CSRF-protected routes and the restricted Unix boundary instead.
"""
import json
import click
from .engine import Engine,UpdateError


@click.group()
def main():
    """Manage the explicitly installed host updater without automatic deployment."""


@main.command('serve')
@click.option('--root',required=True)
def serve_command(root):
    """Run independent host controls and read-only LAN HTTP status until systemd stops them."""
    from .service import serve
    serve(root)


@main.command('status')
@click.option('--root',required=True)
def status(root):
    """Print retained real status for diagnosing interrupted updates over SSH."""
    click.echo(json.dumps(Engine(root).state(),indent=2))


@main.command('check')
@click.option('--root',required=True)
def check(root):
    """Fetch approved main metadata without stopping or migrating the application."""
    try: click.echo(json.dumps(Engine(root).check(),indent=2))
    except UpdateError as error: raise click.ClickException(str(error)) from error


@main.command('update')
@click.option('--root',required=True)
@click.option('--confirm',is_flag=True)
@click.option('--allow-migration',is_flag=True)
def update(root,confirm,allow_migration):
    """Emergency operator update reuses the same engine as the browser service."""
    engine=Engine(root)
    try:
        release=engine.check()
        click.echo(f"Approved {release['version']} / schema {release['schema']} / {release['id']}")
        if not confirm: click.confirm('Install this approved release with a verified backup?',abort=True)
        if not allow_migration:
            schema,_,_=engine.storage()
            if release['schema']>schema:
                phrase=click.prompt(f"Type MIGRATE {release['schema']} to approve candidate migration")
                if phrase!=f"MIGRATE {release['schema']}": raise click.ClickException('Migration declined.')
                allow_migration=True
        engine.install(release['id'],confirm=True,migration_confirm=allow_migration)
    except UpdateError as error: raise click.ClickException(str(error)) from error


if __name__=='__main__': main()
