# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'hospitalq-secret-2024'
    )

    RAW_DB_URL = os.environ.get('DATABASE_URL', '')

    if RAW_DB_URL:
        if RAW_DB_URL.startswith('postgres://'):
            RAW_DB_URL = RAW_DB_URL.replace(
                'postgres://', 'postgresql://', 1
            )
        SQLALCHEMY_DATABASE_URI = RAW_DB_URL
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