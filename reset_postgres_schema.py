"""
Resets your Postgres database to match the CURRENT model definitions
exactly, by dropping every table this app knows about and letting the
app recreate them fresh and correct on its next startup.

Only run this if the target database has no real data you need to
keep — this deletes everything in it. It exists specifically to fix
the situation where an early, incomplete deploy already created some
tables with an outdated schema, and db.create_all() won't touch them
again because (as far as it's concerned) they already exist.

Usage:
    1. Get your Postgres connection string from Render's dashboard —
       use the "External Database URL", since you're running this
       from your own machine, not from inside Render.
    2. Set DATABASE_URL to that connection string:
         Windows (PowerShell): $env:DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
    3. Run: python reset_postgres_schema.py
    4. Redeploy (or just restart) your Render service — app.py will
       recreate every table correctly and reseed default data on boot.
"""
import os
import sys


def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: Set DATABASE_URL to your Postgres connection string first.")
        sys.exit(1)

    if not database_url.startswith('postgres'):
        print("ERROR: DATABASE_URL doesn't look like a Postgres URL — refusing to")
        print("       continue, so this can't accidentally wipe the wrong database.")
        sys.exit(1)

    from flask import Flask
    from config import Config
    from db import db

    # Import every model so SQLAlchemy's metadata knows about all of
    # them — same reasoning as the app.py fix: drop_all()/create_all()
    # only act on models Python has actually imported.
    from models.hospital_model import Hospital   # noqa: F401
    from models.user_model     import User        # noqa: F401
    from models.queue_model    import Queue        # noqa: F401
    from models.token_model    import Token        # noqa: F401
    from models.otp_model      import PasswordResetOTP  # noqa: F401

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    confirm = input(
        f"This will DELETE ALL TABLES at:\n  {database_url}\n"
        f"Type 'yes' to continue: "
    )
    if confirm.strip().lower() != 'yes':
        print("Cancelled — nothing was changed.")
        sys.exit(0)

    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables fresh from current models...")
        db.create_all()
        print("Done. Restart your Render service to reseed default data.")


if __name__ == '__main__':
    main()