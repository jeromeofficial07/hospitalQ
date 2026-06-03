from db import db
import datetime

class Token(db.Model):
    __tablename__ = 'tokens'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    queue_id     = db.Column(
        db.Integer,
        db.ForeignKey('queues.id'),
        nullable=False
    )
    token_number = db.Column(db.String(20), nullable=False)
    status       = db.Column(db.String(20), default='waiting')
    created_at   = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow
    )

    def to_dict(self):
        return {
            'id':           self.id,
            'token_number': self.token_number,
            'status':       self.status,
            'queue_id':     self.queue_id,
            'user_id':      self.user_id,
            'created_at':   self.created_at.strftime(
                '%Y-%m-%d %H:%M:%S'
            )
        }