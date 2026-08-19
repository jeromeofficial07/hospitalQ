# app.py
import os
from flask import Flask
from flask_socketio import SocketIO
from sqlalchemy import event
from sqlalchemy.engine import Engine
from config import Config
from db import db

# 'threading' — what you've been running locally, including on
# Windows, where 'eventlet' has a history of install/compatibility
# issues. Set ASYNC_MODE=eventlet in your production environment
# (Linux hosting) for real concurrent SocketIO connections instead
# of one-thread-per-connection.
ASYNC_MODE = os.environ.get('ASYNC_MODE', 'threading')

socketio = SocketIO(async_mode=ASYNC_MODE)


# Performance: by default SQLite locks the whole database on any
# write, so a busy no-show watcher + SocketIO events + normal page
# requests all fighting over the same file causes visible stalls.
# WAL mode lets reads happen concurrently with writes, and a busy
# timeout means a request waits briefly for a lock instead of
# throwing "database is locked" immediately.
@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    if not dbapi_connection.__class__.__module__.startswith('sqlite3'):
        return  # only applies to SQLite; harmless no-op on any other DB
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins="*"
    )

    from routes.auth_routes  import auth_bp
    from routes.queue_routes import queue_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(admin_bp)

    @app.template_filter('dept_color')
    def dept_color_filter(index):
        colors = ['#e11d48','#be123c','#f43f5e','#fb7185']
        return colors[(index - 1) % len(colors)]

    @app.template_filter('dept_icon')
    def dept_icon_filter(name):
        icons = {
            'OPD':        '🏥',
            'Pharmacy':   '💊',
            'Laboratory': '🧪',
            'Radiology':  '🩻',
            'Emergency':  '🚨',
            'Cardiology': '❤️',
            'Pediatrics': '👶',
            'Gynecology': '🤱',
            'Orthopedics':'🦴',
            'Dental':     '🦷',
            'Neurology':  '🧠',
            'Billing':    '💳'
        }
        return icons.get(name, '🏥')

    # Create all tables and default data automatically.
    #
    # IMPORTANT: db.create_all() only creates tables for models that
    # Python has already imported by this point — it inspects
    # SQLAlchemy's metadata, which only knows about a model once its
    # class definition has executed somewhere. Relying on blueprint
    # imports above to have pulled in every model as a side effect is
    # fragile (this broke exactly that way: Hospital was only ever
    # imported inside insert_default_data(), which runs AFTER this
    # call, so on a brand-new database the hospitals table silently
    # never got created). Import every model explicitly here so this
    # doesn't depend on import order elsewhere in the app.
    with app.app_context():
        from models.hospital_model import Hospital   # noqa: F401
        from models.user_model     import User        # noqa: F401
        from models.queue_model    import Queue        # noqa: F401
        from models.token_model    import Token        # noqa: F401
        from models.otp_model      import PasswordResetOTP  # noqa: F401

        db.create_all()
        insert_default_data()

    # NEW: background watcher that auto-cancels/requeues tokens nobody
    # showed up for, so a silent no-show doesn't freeze a queue forever.
    socketio.start_background_task(no_show_watcher, app)

    return app


def no_show_watcher(app):
    from queue_engine import check_no_shows, NO_SHOW_GRACE_SECONDS

    # Check a bit more often than the grace period so a no-show is
    # caught soon after it actually expires, not way after.
    poll_interval = max(NO_SHOW_GRACE_SECONDS // 4, 15)

    while True:
        try:
            check_no_shows(app)
        except Exception:
            pass
        socketio.sleep(poll_interval)


def insert_default_data():
    from models.hospital_model import Hospital
    from models.queue_model    import Queue
    from models.user_model     import User

    # Every department and hospital-admin belongs to a hospital, so
    # make sure at least one exists before seeding anything else.
    default_hospital = Hospital.query.filter_by(slug='default').first()
    if not default_hospital:
        default_hospital = Hospital(
            name='General Hospital',
            slug='default',
            status='active'
        )
        db.session.add(default_hospital)
        db.session.commit()  # need its id before FK-ing departments/admin to it

    # Insert default hospital departments if not exist
    departments = [
        'OPD',
        'Pharmacy',
        'Laboratory',
        'Radiology',
        'Emergency',
        'Cardiology',
        'Pediatrics',
        'Billing'
    ]

    for dept in departments:
        exists = Queue.query.filter_by(
            department_name=dept,
            hospital_id=default_hospital.id
        ).first()
        if not exists:
            q = Queue(
                department_name=dept,
                status='active',
                hospital_id=default_hospital.id
            )
            db.session.add(q)

    # Default admin for the default hospital, if not exist
    admin_exists = User.query.filter_by(
        role='admin', hospital_id=default_hospital.id
    ).first()
    if not admin_exists:
        admin = User(
            name        = 'Hospital Admin',
            email       = 'admin@hospital.com',
            role        = 'admin',
            hospital_id = default_hospital.id
        )
        admin.set_password('admin123')
        db.session.add(admin)

    # NEW: platform-level super admin, who can create/manage hospitals
    # and their admins. Not scoped to any single hospital_id.
    super_admin_exists = User.query.filter_by(role='super_admin').first()
    if not super_admin_exists:
        super_admin = User(
            name  = 'Platform Owner',
            email = 'superadmin@queueflow.com',
            role  = 'super_admin'
        )
        super_admin.set_password('superadmin123')
        db.session.add(super_admin)

    db.session.commit()


app = create_app()

if __name__ == '__main__':
    # DEBUG defaults to on for local dev. In production you run this
    # via gunicorn instead of `python app.py`, so this block doesn't
    # even execute there — but the env var is a safety net in case
    # something ever does invoke this file directly on a server.
    debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'
    socketio.run(app, debug=debug_mode)