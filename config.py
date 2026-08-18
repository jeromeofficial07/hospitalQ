import os
from dotenv import load_dotenv

load_dotenv()  # reads a local .env file if present — never commit that file

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _resolve_database_uri():
    """
    Production: set DATABASE_URL to your Postgres connection string
    and this is used automatically — no code change needed to deploy.

    Local dev: leave DATABASE_URL unset and it falls back to the same
    SQLite file as before, so nothing changes for local development.
    """
    url = os.environ.get('DATABASE_URL')

    if not url:
        return 'sqlite:///' + os.path.join(BASE_DIR, 'queueflow.db')

    # Some providers (Heroku, older Render configs) still hand out
    # "postgres://" URLs, but SQLAlchemy 1.4+/2.x requires the
    # "postgresql://" scheme. Fix it up transparently so copy-pasting
    # a connection string from your provider's dashboard just works.
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)

    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'queueflow-hospital-secret-2024')

    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Keeps connections healthy across Postgres providers that close
    # idle connections after a few minutes (very common on free/
    # shared tiers) — without this you'd intermittently see
    # "SSL connection has been closed unexpectedly" errors.
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

    # ── Email OTP (forgot password) ──
    # Reads from environment variables so real credentials never sit
    # in source control. Set these before running the app:
    #
    #   Windows (PowerShell):
    #     $env:MAIL_USERNAME = "youraddress@gmail.com"
    #     $env:MAIL_PASSWORD = "your-16-char-app-password"
    #
    #   Mac/Linux:
    #     export MAIL_USERNAME="youraddress@gmail.com"
    #     export MAIL_PASSWORD="your-16-char-app-password"
    #
    # IMPORTANT: MAIL_PASSWORD must be a Gmail "App Password", not your
    # normal Gmail password — Google blocks plain-password SMTP logins.
    # Generate one at: https://myaccount.google.com/apppasswords
    # (requires 2-Step Verification to be turned on for the account).
    #
    # If these are left unset, OTPs still "send" — the app just logs
    # the code to the console instead of emailing it, so you can keep
    # developing and testing the flow without real credentials yet.
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # ── SMS OTP (forgot password, optional) ──
    # Not wired to a real provider yet — needs a Twilio (or similar)
    # account. See send_sms_otp() in routes/auth_routes.py for where
    # to plug in real credentials once you have them.
    TWILIO_ACCOUNT_SID  = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN   = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_FROM_NUMBER  = os.environ.get('TWILIO_FROM_NUMBER')