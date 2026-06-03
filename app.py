# app.py
import os
import threading
import time
import urllib.request

from flask import Flask
from flask_socketio import SocketIO
from config import Config
from db import db

socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Auto detect environment
    # Production (Render) = gevent
    # Local development   = threading
    is_production = os.environ.get('FLASK_ENV') == 'production'

    if is_production:
        async_mode = 'gevent'
    else:
        async_mode = 'threading'

    socketio.init_app(
        app,
        cors_allowed_origins = '*',
        async_mode           = async_mode,
        ping_timeout         = 60,
        ping_interval        = 25
    )

    from routes.auth_routes  import auth_bp
    from routes.queue_routes import queue_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(admin_bp)

    @app.template_filter('dept_color')
    def dept_color_filter(index):
        colors = [
            '#e11d48', '#be123c',
            '#f43f5e', '#fb7185'
        ]
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
            'Billing':    '💳'
        }
        return icons.get(name, '🏥')

    @app.route('/ping')
    def ping():
        return 'pong', 200

    with app.app_context():
        db.create_all()
        insert_default_data()

    return app


def insert_default_data():
    from models.queue_model import Queue
    from models.user_model  import User

    departments = [
        'OPD', 'Pharmacy', 'Laboratory',
        'Radiology', 'Emergency', 'Cardiology',
        'Pediatrics', 'Billing'
    ]

    for dept in departments:
        exists = Queue.query.filter_by(
            department_name=dept
        ).first()
        if not exists:
            q = Queue(
                department_name=dept,
                status='active'
            )
            db.session.add(q)

    admin_exists = User.query.filter_by(
        role='admin'
    ).first()

    if not admin_exists:
        admin = User(
            name  = 'Hospital Admin',
            email = 'admin@hospital.com',
            role  = 'admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

    try:
        db.session.commit()
    except Exception as e:
        print('Default data error: ' + str(e))
        db.session.rollback()


def keep_alive():
    app_url = os.environ.get('APP_URL', '')
    if not app_url:
        return
    time.sleep(60)
    while True:
        try:
            urllib.request.urlopen(
                app_url + '/ping',
                timeout=10
            )
            print('Keep-alive: OK')
        except Exception as e:
            print('Keep-alive failed: ' + str(e))
        time.sleep(14 * 60)


app = create_app()

if os.environ.get('APP_URL'):
    t = threading.Thread(
        target=keep_alive,
        daemon=True
    )
    t.start()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(
        app,
        host  = '0.0.0.0',
        port  = port,
        debug = True
    )