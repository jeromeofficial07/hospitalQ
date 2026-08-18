# models/hospital_model.py
from db import db


class Hospital(db.Model):
    __tablename__ = 'hospitals'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False)
    slug       = db.Column(db.String(60),  unique=True, nullable=False)  # url-friendly id, e.g. 'city-general'
    address    = db.Column(db.String(255), nullable=True)
    phone      = db.Column(db.String(30),  nullable=True)
    status     = db.Column(db.String(20),  default='active')  # active | inactive
    created_at = db.Column(
        db.DateTime, default=db.func.current_timestamp()
    )

    queues = db.relationship('Queue', backref='hospital', lazy=True)
    admins = db.relationship('User',  backref='hospital', lazy=True)

    def to_dict(self):
        from models.queue_model import Queue
        dept_count = Queue.query.filter_by(hospital_id=self.id).count()
        return {
            'id':         self.id,
            'name':       self.name,
            'slug':       self.slug,
            'address':    self.address,
            'phone':      self.phone,
            'status':     self.status,
            'dept_count': dept_count
        }