from db import db
import datetime

class Queue(db.Model):
    __tablename__ = 'queues'

    id              = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), nullable=False)
    status          = db.Column(db.String(20), default='active')
    created_at      = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow
    )

    tokens = db.relationship(
        'Token', backref='queue', lazy='select'
    )

    def to_dict(self):
        from models.token_model import Token
        waiting = Token.query.filter_by(
            queue_id = self.id,
            status   = 'waiting'
        ).count()
        return {
            'id':              self.id,
            'department_name': self.department_name,
            'status':          self.status,
            'waiting_count':   waiting
        }