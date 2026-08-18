from db import db
from datetime import datetime

class Token(db.Model):
    __tablename__ = 'tokens'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True
    )
    queue_id     = db.Column(
        db.Integer,
        db.ForeignKey('queues.id'),
        nullable=False,
        index=True
    )
    token_number = db.Column(db.String(20),  nullable=False)
    status       = db.Column(db.String(20),  default='waiting', index=True)
    created_at   = db.Column(
        db.DateTime, default=datetime.utcnow, index=True
    )

    # NEW: lets us measure real service duration instead of guessing
    called_at    = db.Column(db.DateTime, nullable=True)  # set when token becomes 'serving'
    completed_at = db.Column(db.DateTime, nullable=True)  # set when token becomes 'completed'
    missed_count = db.Column(db.Integer, default=0)       # number of times this token was called with no response

    # This exact combination (queue_id + status, ordered by created_at)
    # is the single most common query in the whole app — every
    # position/wait-time calculation, every "next token" call, every
    # live-queue poll hits it. One composite index covers all of them.
    __table_args__ = (
        db.Index('ix_tokens_queue_status_created', 'queue_id', 'status', 'created_at'),
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