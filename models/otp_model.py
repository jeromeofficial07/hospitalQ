# models/otp_model.py
import random
from datetime import datetime
from db import db


class PasswordResetOTP(db.Model):
    __tablename__ = 'password_reset_otps'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    # The OTP is hashed, same as passwords — if the DB ever leaks,
    # nobody can replay a still-valid reset code straight from it.
    otp_hash   = db.Column(db.String(255), nullable=False)
    channel    = db.Column(db.String(10),  nullable=False)  # 'email' or 'sms'
    expires_at = db.Column(db.DateTime,    nullable=False)
    used       = db.Column(db.Boolean,     default=False)
    attempts   = db.Column(db.Integer,     default=0)  # wrong-code attempts against this OTP
    created_at = db.Column(db.DateTime,    default=datetime.utcnow, index=True)

    @staticmethod
    def generate_code():
        """6-digit numeric code, e.g. '048213'."""
        return f"{random.randint(0, 999999):06d}"