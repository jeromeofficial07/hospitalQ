from db import db

class Queue(db.Model):
    __tablename__ = 'queues'

    id              = db.Column(db.Integer, primary_key=True)
    hospital_id     = db.Column(
        db.Integer, db.ForeignKey('hospitals.id'), nullable=False, index=True
    )
    department_name = db.Column(db.String(100), nullable=False)
    status          = db.Column(db.String(20),  default='active', index=True)
    created_at      = db.Column(
        db.DateTime, default=db.func.current_timestamp()
    )

    tokens = db.relationship(
        'Token', backref='queue', lazy=True
    )

    def to_dict(self):
        from models.token_model import Token
        waiting = Token.query.filter_by(
            queue_id=self.id,
            status='waiting'
        ).count()
        return {
            'id':              self.id,
            'hospital_id':     self.hospital_id,
            'department_name': self.department_name,
            'status':          self.status,
            'waiting_count':   waiting
        }