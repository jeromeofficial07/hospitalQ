"""
Migration for multi-hospital support, on top of the earlier
called_at/completed_at/missed_count migration.

Run once from your project root:
    python migrate_db.py

Safe to re-run - every step checks before acting.
"""
import sqlite3

DB_PATH = 'queueflow.db'


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def table_exists(cur, table):
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cur.fetchone() is not None


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # -- earlier migration: no-show tracking --
    if not column_exists(cur, 'tokens', 'called_at'):
        cur.execute("ALTER TABLE tokens ADD COLUMN called_at DATETIME")
        print("Added tokens.called_at")
    else:
        print("tokens.called_at already exists - skipped")

    if not column_exists(cur, 'tokens', 'completed_at'):
        cur.execute("ALTER TABLE tokens ADD COLUMN completed_at DATETIME")
        print("Added tokens.completed_at")
    else:
        print("tokens.completed_at already exists - skipped")

    if not column_exists(cur, 'tokens', 'missed_count'):
        cur.execute("ALTER TABLE tokens ADD COLUMN missed_count INTEGER DEFAULT 0")
        print("Added tokens.missed_count")
    else:
        print("tokens.missed_count already exists - skipped")

    # -- NEW: multi-hospital support --
    if not table_exists(cur, 'hospitals'):
        cur.execute("""
            CREATE TABLE hospitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL,
                slug VARCHAR(60) UNIQUE NOT NULL,
                address VARCHAR(255),
                phone VARCHAR(30),
                status VARCHAR(20) DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created hospitals table")
    else:
        print("hospitals table already exists - skipped")

    if not column_exists(cur, 'queues', 'hospital_id'):
        cur.execute("ALTER TABLE queues ADD COLUMN hospital_id INTEGER")
        print("Added queues.hospital_id")
    else:
        print("queues.hospital_id already exists - skipped")

    if not column_exists(cur, 'users', 'hospital_id'):
        cur.execute("ALTER TABLE users ADD COLUMN hospital_id INTEGER")
        print("Added users.hospital_id")
    else:
        print("users.hospital_id already exists - skipped")

    # -- NEW: forgot-password via OTP --
    if not column_exists(cur, 'users', 'phone'):
        cur.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
        print("Added users.phone")
    else:
        print("users.phone already exists - skipped")

    if not table_exists(cur, 'password_reset_otps'):
        cur.execute("""
            CREATE TABLE password_reset_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                otp_hash VARCHAR(255) NOT NULL,
                channel VARCHAR(10) NOT NULL,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT 0,
                attempts INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        print("Created password_reset_otps table")
    else:
        print("password_reset_otps table already exists - skipped")

    con.commit()

    # -- Backfill: everything that existed before this migration
    #    belongs to one default hospital, so nothing breaks. --
    cur.execute("SELECT id FROM hospitals WHERE slug = 'default'")
    row = cur.fetchone()
    if row:
        default_hospital_id = row[0]
        print(f"Default hospital already exists (id={default_hospital_id})")
    else:
        cur.execute("""
            INSERT INTO hospitals (name, slug, address, phone, status)
            VALUES (?, ?, ?, ?, ?)
        """, ('General Hospital', 'default', '', '', 'active'))
        default_hospital_id = cur.lastrowid
        print(f"Created default hospital (id={default_hospital_id})")

    cur.execute(
        "UPDATE queues SET hospital_id = ? WHERE hospital_id IS NULL",
        (default_hospital_id,)
    )
    print(f"Backfilled {cur.rowcount} department(s) into the default hospital")

    cur.execute(
        "UPDATE users SET hospital_id = ? WHERE role = 'admin' AND hospital_id IS NULL",
        (default_hospital_id,)
    )
    print(f"Backfilled {cur.rowcount} existing admin(s) into the default hospital")

    con.commit()

    # -- Performance: indexes on every column the app actually
    #    filters/sorts by. Safe to re-run - IF NOT EXISTS guards it. --
    index_statements = [
        "CREATE INDEX IF NOT EXISTS ix_tokens_user_id ON tokens (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_tokens_queue_id ON tokens (queue_id)",
        "CREATE INDEX IF NOT EXISTS ix_tokens_status ON tokens (status)",
        "CREATE INDEX IF NOT EXISTS ix_tokens_created_at ON tokens (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_tokens_queue_status_created ON tokens (queue_id, status, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_queues_hospital_id ON queues (hospital_id)",
        "CREATE INDEX IF NOT EXISTS ix_queues_status ON queues (status)",
        "CREATE INDEX IF NOT EXISTS ix_users_hospital_id ON users (hospital_id)",
        "CREATE INDEX IF NOT EXISTS ix_password_reset_otps_user_id ON password_reset_otps (user_id)",
    ]
    for stmt in index_statements:
        cur.execute(stmt)
    print(f"Ensured {len(index_statements)} performance indexes exist")

    # -- Performance: WAL mode lets reads and writes happen
    #    concurrently instead of blocking each other, which matters a
    #    lot here since the no-show watcher, SocketIO events, and
    #    regular page requests are all hitting SQLite at once. --
    cur.execute("PRAGMA journal_mode=WAL")
    mode = cur.fetchone()
    print(f"SQLite journal mode: {mode[0] if mode else 'unknown'}")

    con.commit()
    con.close()
    print("Migration complete.")


if __name__ == '__main__':
    main()