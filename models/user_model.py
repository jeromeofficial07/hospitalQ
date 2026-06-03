from db import db
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
import datetime

class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(
        db.String(100), unique=True, nullable=False
    )
    password   = db.Column(db.String(255), nullable=False)
    role       = db.Column(db.String(20), default='user')
    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow
    )

    tokens = db.relationship(
        'Token', backref='user', lazy='select'
    )

    def set_password(self, raw):
        self.password = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password, raw)

    def to_dict(self):
        return {
            'id':    self.id,
            'name':  self.name,
            'email': self.email,
            'role':  self.role
        }