# queue_engine.py
"""
Shared queue-advancement logic. Both the manual "Next Token" admin
button and the automatic no-show watcher call into this module so
they can never drift out of sync with each other.
"""
from datetime import datetime
from db import db

NO_SHOW_GRACE_SECONDS = 120   # how long a called token gets before it's treated as a no-show
MAX_MISSED_CALLS      = 3     # after this many misses, the token is cancelled outright


def get_socketio():
    from app import socketio
    return socketio


def advance_queue(queue_id):
    """
    Marks the currently-serving token (if any) as completed and calls
    the next waiting token. Returns the newly-serving Token or None.
    """
    from models.token_model import Token

    serving = Token.query.filter_by(
        queue_id=queue_id, status='serving'
    ).first()
    if serving:
        serving.status = 'completed'
        serving.completed_at = datetime.utcnow()
        db.session.commit()

        from routes.queue_routes import invalidate_avg_cache
        invalidate_avg_cache(queue_id)

    nxt = (
        Token.query
        .filter_by(queue_id=queue_id, status='waiting')
        .order_by(Token.created_at)
        .first()
    )
    if nxt:
        nxt.status = 'serving'
        nxt.called_at = datetime.utcnow()
        db.session.commit()
        _emit_next_token(nxt)
        _emit_wait_time_update(queue_id)

    return nxt


def mark_no_show(queue_id, reason='manual'):
    """
    Handles the token currently being served in a queue when the
    patient doesn't show up. The first couple of misses send the
    token back to the end of the line for another chance; after
    MAX_MISSED_CALLS it's cancelled outright. Either way, the queue
    then automatically advances to whoever is next.

    reason: 'manual' (admin clicked "No Show") or 'auto' (grace
    period expired with nobody responding).
    """
    from models.token_model import Token

    serving = Token.query.filter_by(
        queue_id=queue_id, status='serving'
    ).first()

    if not serving:
        return None

    serving.missed_count = (serving.missed_count or 0) + 1

    result = {
        'token_id':     serving.id,
        'token_number': serving.token_number,
        'queue_id':     queue_id,
        'missed_count': serving.missed_count,
        'reason':       reason
    }

    if serving.missed_count >= MAX_MISSED_CALLS:
        serving.status = 'cancelled'
        serving.completed_at = datetime.utcnow()
        result['cancelled'] = True
    else:
        # Requeue at the back rather than cancel outright — bumping
        # created_at is what actually sends it to the end of the
        # FIFO line, since position is ordered by created_at.
        serving.status = 'waiting'
        serving.called_at = None
        serving.created_at = datetime.utcnow()
        result['cancelled'] = False

    db.session.commit()

    try:
        get_socketio().emit('no_show', result)
    except Exception:
        pass

    advance_queue(queue_id)

    return result


def check_no_shows(app):
    """
    Scans every active queue for a currently-serving token that has
    gone past the grace period with no admin action, and treats it
    as an automatic no-show. Needs the Flask app to open its own
    app context since this runs in a background thread.
    """
    with app.app_context():
        from models.queue_model import Queue
        from models.token_model import Token

        now = datetime.utcnow()

        queues = Queue.query.filter_by(status='active').all()
        for q in queues:
            serving = Token.query.filter_by(
                queue_id=q.id, status='serving'
            ).first()
            if not serving or not serving.called_at:
                continue

            elapsed = (now - serving.called_at).total_seconds()
            if elapsed >= NO_SHOW_GRACE_SECONDS:
                mark_no_show(q.id, reason='auto')


def _emit_next_token(token):
    try:
        get_socketio().emit('next_token', {
            'token_number': token.token_number,
            'queue_id':     token.queue_id,
            'user_id':      token.user_id
        })
        get_socketio().emit('queue_update', {
            'queue_id': token.queue_id
        })
    except Exception:
        pass


def _emit_wait_time_update(queue_id):
    from models.token_model import Token
    from routes.queue_routes import estimate_wait_minutes

    still_waiting = (
        Token.query
        .filter_by(queue_id=queue_id, status='waiting')
        .order_by(Token.created_at)
        .all()
    )
    estimates = [
        {
            'token_id':  t.id,
            'position':  i,
            'est_wait':  estimate_wait_minutes(queue_id, i)
        }
        for i, t in enumerate(still_waiting)
    ]
    try:
        get_socketio().emit('wait_time_update', {
            'queue_id':  queue_id,
            'estimates': estimates
        })
    except Exception:
        pass