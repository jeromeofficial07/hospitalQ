import os

class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY',
        'hospitalq-secret-2024'
    )

    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    if DATABASE_URL:
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace(
                'postgres://', 'postgresql://', 1
            )
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = (
            'sqlite:///'
            + os.path.join(BASE_DIR, 'hospitalq.db')
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle':  280
    }