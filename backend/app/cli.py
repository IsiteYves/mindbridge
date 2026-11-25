"""Two periodic jobs, each a one-shot command meant to be triggered by
whatever free scheduler the deployment already has available.

    flask reminders send      one pass of app/services/reminders.py
    flask canvas sync-all     one pass re-syncing every connected account
"""

import datetime as dt

import click
from flask import current_app
from flask.cli import AppGroup

from app.extensions import db
from app.models import LMSIntegration
from app.services.canvas import CanvasClient, CanvasError
from app.services.canvas_sync import sync_courses
from app.services.crypto import EncryptionNotConfigured, decrypt_secret
from app.services.reminders import send_due_reminders

reminders_cli = AppGroup("reminders", help="Send due reminder emails.")
canvas_cli = AppGroup("canvas", help="Keep connected Canvas accounts in sync.")


@reminders_cli.command("send")
def send():
    """Send every reminder due today, then print a one-line summary."""
    result = send_due_reminders()
    click.echo(f"considered={result['considered']} sent={result['sent']}")


@canvas_cli.command("sync-all")
def sync_all():
    """Re-sync every account with an active Canvas connection"""
    base_url = current_app.config.get("CANVAS_BASE_URL")
    if not base_url:
        click.echo("Canvas integration is not configured on this server; nothing to sync.")
        return

    synced, failed = 0, 0
    connections = db.session.query(LMSIntegration).filter_by(provider="canvas", status="connected")
    for integration in connections:
        course_ids = integration.selected_course_ids or []
        if not course_ids:
            continue
        try:
            token = decrypt_secret(integration.access_token_encrypted)
            if token is None:
                raise CanvasError("stored token could not be read back", 409)
            client = CanvasClient(base_url, token)
            sync_courses(integration.user, client, course_ids)
            integration.last_synced_at = dt.datetime.now(dt.timezone.utc)
            db.session.commit()
            synced += 1
        # One failing account is disconnected and skipped so it does not block the rest.
        except (CanvasError, EncryptionNotConfigured) as error:
            db.session.rollback()
            integration.status = "disconnected"
            db.session.commit()
            failed += 1
            click.echo(f"user_id={integration.user_id} failed and was disconnected: {error}")

    click.echo(f"synced={synced} failed={failed}")


def register(app):
    app.cli.add_command(reminders_cli)
    app.cli.add_command(canvas_cli)