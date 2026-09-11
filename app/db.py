import sqlite3
from pathlib import Path

import click
from flask import current_app, g

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


@click.command("init-db")
def init_db_command():
    """Recree les tables (supprime les donnees existantes)."""
    init_db()
    click.echo("Base de donnees initialisee.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
