from db import db
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

class User(db.Model):
    __tablename__ = 'users'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(100), unique=True, nullable=False)
    phone       = db.Column(db.String(20),  unique=True, nullable=True)  # optional, enables SMS password reset
    password    = db.Column(db.String(255), nullable=False)
    role        = db.Column(db.String(20),  default='user')  # user | admin | super_admin
    # NEW: which hospital this account belongs to.
    # - role='user'         -> always NULL, patients aren't tied to one hospital
    # - role='admin'        -> the hospital they manage
    # - role='super_admin'  -> always NULL, they manage every hospital
    hospital_id = db.Column(
        db.Integer, db.ForeignKey('hospitals.id'), nullable=True
    )
    created_at  = db.Column(
        db.DateTime, default=db.func.current_timestamp()
    )

    tokens = db.relationship('Token', backref='user', lazy=True)

    def set_password(self, raw):
        self.password = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password, raw)

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'email':       self.email,
            'phone':       self.phone,
            'role':        self.role,
            'hospital_id': self.hospital_id
        }