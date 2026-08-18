"""
One-time data migration: copies everything from your local
queueflow.db (SQLite) into whatever Postgres database DATABASE_URL
points to.

Usage:
    1. Create a Postgres database with your hosting provider and get
       its connection string.
    2. Set DATABASE_URL to that connection string:
         Windows (PowerShell): $env:DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
         Mac/Linux:            export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    3. Make sure queueflow.db (your OLD SQLite file) is in this folder.
    4. Run: python migrate_to_postgres.py

This only fills an EMPTY Postgres database — if a table already has
rows in Postgres, that table is skipped rather than risking
duplicates. Safe to re-run.
"""
import os
import sys
import sqlite3

SQLITE_PATH = 'queueflow.db'


def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: Set DATABASE_URL to your Postgres connection string first. See the")
        print("       instructions at the top of this file.")
        sys.exit(1)

    if not database_url.startswith('postgres'):
        print("ERROR: DATABASE_URL doesn't look like a Postgres URL — refusing to continue")
        print("       so this can't accidentally overwrite the wrong database.")
        sys.exit(1)

    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: {SQLITE_PATH} not found in this folder. Run this script from your")
        print("       project root, next to your existing SQLite file.")
        sys.exit(1)

    # Deliberately NOT importing from app.py here — create_app() would
    # auto-seed a default hospital/admin into the new Postgres database
    # before we get a chance to copy the REAL data over, which would
    # throw off the "table already has rows, skip it" safety check
    # below. Build a bare app just for database access instead.
    from flask import Flask
    from config import Config
    from db import db

    from models.hospital_model import Hospital
    from models.user_model     import User
    from models.queue_model    import Queue
    from models.token_model    import Token
    from models.otp_model      import PasswordResetOTP

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    sqlite_con = sqlite3.connect(SQLITE_PATH)
    sqlite_con.row_factory = sqlite3.Row

    # Order matters — each table's foreign keys must already exist
    # in the ones before it (hospitals before users/queues, queues
    # before tokens, users before tokens/otps).
    tables = [
        ('hospitals', Hospital,
         ['id', 'name', 'slug', 'address', 'phone', 'status', 'created_at']),
        ('users', User,
         ['id', 'name', 'email', 'phone', 'password', 'role', 'hospital_id', 'created_at']),
        ('queues', Queue,
         ['id', 'hospital_id', 'department_name', 'status', 'created_at']),
        ('tokens', Token,
         ['id', 'user_id', 'queue_id', 'token_number', 'status', 'created_at',
          'called_at', 'completed_at', 'missed_count']),
        ('password_reset_otps', PasswordResetOTP,
         ['id', 'user_id', 'otp_hash', 'channel', 'expires_at', 'used', 'attempts', 'created_at']),
    ]

    with app.app_context():
        print("Creating tables in Postgres (if they don't already exist)...")
        db.create_all()

        for table_name, model, columns in tables:
            if not _sqlite_table_exists(sqlite_con, table_name):
                print(f"{table_name}: not present in SQLite — skipping")
                continue

            rows = sqlite_con.execute(f"SELECT * FROM {table_name}").fetchall()
            print(f"{table_name}: {len(rows)} row(s) found in SQLite")

            existing = model.query.count()
            if existing > 0:
                print(f"  Skipping — Postgres already has {existing} row(s) in "
                      f"{table_name}. Only copies into an empty table.")
                continue

            count = 0
            for row in rows:
                row_keys = row.keys()
                kwargs = {col: row[col] for col in columns if col in row_keys}
                db.session.add(model(**kwargs))
                count += 1
            db.session.commit()
            print(f"  Inserted {count} row(s) into {table_name}")

        # Postgres tracks auto-increment IDs with a sequence that
        # doesn't know about the explicit IDs we just inserted — the
        # next auto-generated row would collide with one we copied
        # over. Bump every sequence past the highest ID now in use.
        print("Resetting Postgres auto-increment sequences...")
        for table_name, _model, _cols in tables:
            try:
                db.session.execute(db.text(
                    f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table_name}), 1))"
                ))
            except Exception as e:
                print(f"  Warning: couldn't reset sequence for {table_name}: {e}")
        db.session.commit()

    sqlite_con.close()
    print("Migration to Postgres complete.")


def _sqlite_table_exists(con, table_name):
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


if __name__ == '__main__':
    main()