# routes/queue_routes.py
from flask import (Blueprint, request, session,
                   redirect, url_for, render_template,
                   jsonify, flash)
from functools import wraps
from datetime import datetime
import time as _time
from models.token_model import Token
from models.queue_model  import Queue
from db import db

queue_bp = Blueprint('queue', __name__)

DEFAULT_SERVICE_SECONDS = 300  # 5 min fallback when there's no history yet
HISTORY_SAMPLE_SIZE     = 10   # how many recent completed tokens to average

def get_socketio():
    from app import socketio
    return socketio

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# Average service time only changes when a token actually completes,
# so recomputing it on every single poll/request was pure waste — it
# was one of the biggest sources of redundant queries in the app.
# Cache it briefly and invalidate on completion instead.
_AVG_CACHE = {}       # queue_id -> (value, expires_at)
_AVG_CACHE_TTL = 20    # seconds


def invalidate_avg_cache(queue_id):
    _AVG_CACHE.pop(queue_id, None)


def get_avg_service_seconds(queue_id):
    """
    Real average handling time for a department, based on the last
    N tokens that were actually called AND completed. Falls back to
    a sane default until enough history exists. Cached briefly since
    this was previously re-queried on every wait-time calculation.
    """
    now = _time.time()
    cached = _AVG_CACHE.get(queue_id)
    if cached and cached[1] > now:
        return cached[0]

    recent = (
        Token.query
        .filter(
            Token.queue_id == queue_id,
            Token.status == 'completed',
            Token.called_at.isnot(None),
            Token.completed_at.isnot(None)
        )
        .order_by(Token.completed_at.desc())
        .limit(HISTORY_SAMPLE_SIZE)
        .all()
    )

    if not recent:
        value = DEFAULT_SERVICE_SECONDS
    else:
        total_seconds = 0
        count = 0
        for t in recent:
            delta = (t.completed_at - t.called_at).total_seconds()
            if delta > 0:  # ignore bad/zero data
                total_seconds += delta
                count += 1
        value = (total_seconds / count) if count else DEFAULT_SERVICE_SECONDS

    _AVG_CACHE[queue_id] = (value, now + _AVG_CACHE_TTL)
    return value


def estimate_wait_minutes(queue_id, position):
    """
    position = number of people strictly ahead of this token in
    the waiting line (not counting whoever is currently being served).
    """
    avg_seconds = get_avg_service_seconds(queue_id)

    # If someone is currently being served, factor in how much of
    # their service is likely already elapsed so estimates don't
    # feel frozen right after a call.
    serving = Token.query.filter_by(
        queue_id=queue_id, status='serving'
    ).first()

    remaining_current = avg_seconds
    if serving and serving.called_at:
        elapsed = (datetime.utcnow() - serving.called_at).total_seconds()
        remaining_current = max(avg_seconds - elapsed, 30)  # never below 30s

    total_seconds = remaining_current + (position * avg_seconds) if serving else position * avg_seconds
    minutes = round(total_seconds / 60)
    return max(minutes, 1) if (position > 0 or serving) else 0


@queue_bp.route('/dashboard')
@login_required
def dashboard():
    queues = Queue.query.filter_by(status='active').all()

    user_tokens = (
        Token.query
        .filter_by(user_id=session['user_id'])
        .order_by(Token.created_at.desc())
        .limit(20)
        .all()
    )

    # Strictly only waiting or serving
    active_token = (
        Token.query
        .filter(
            Token.user_id == session['user_id'],
            Token.status.in_(['waiting', 'serving'])
        )
        .order_by(Token.created_at.desc())
        .first()
    )

    return render_template(
        'dashboard.html',
        queues       = queues,
        tokens       = user_tokens,
        active_token = active_token
    )


@queue_bp.route('/my-token')
@login_required
def my_token():
    active_token = (
        Token.query
        .filter(
            Token.user_id == session['user_id'],
            Token.status.in_(['waiting', 'serving'])
        )
        .order_by(Token.created_at.desc())
        .first()
    )

    queue_info = None
    position   = 0
    est_wait   = 0

    if active_token:
        queue_info = Queue.query.get(active_token.queue_id)
        position   = (
            Token.query
            .filter(
                Token.queue_id == active_token.queue_id,
                Token.status   == 'waiting',
                Token.id       <  active_token.id
            )
            .count()
        )
        est_wait = estimate_wait_minutes(active_token.queue_id, position)

    return render_template(
        'my_token.html',
        active_token = active_token,
        queue_info   = queue_info,
        position     = position,
        est_wait     = est_wait
    )


@queue_bp.route('/generate-token', methods=['POST'])
@login_required
def generate_token():
    queue_id = request.form.get('queue_id')
    if not queue_id:
        flash('Please select a department.', 'error')
        return redirect(url_for('queue.dashboard'))

    queue = Queue.query.get_or_404(queue_id)
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Fresh DB check for active token
    existing = (
        Token.query
        .filter(
            Token.user_id == session['user_id'],
            Token.status.in_(['waiting', 'serving'])
        )
        .first()
    )

    if existing:
        msg = ('You already have active token ' + existing.token_number
               + '. Please cancel it first.')
        if wants_json:
            return jsonify({'success': False, 'message': msg})
        flash(msg, 'warning')
        return redirect(url_for('queue.dashboard'))

    # Generate token number
    count        = Token.query.filter_by(
                       queue_id=queue_id
                   ).count()
    prefix       = queue.department_name[:3].upper()
    token_number = prefix + '-' + str(count + 1).zfill(3)

    new_token = Token(
        user_id      = session['user_id'],
        queue_id     = int(queue_id),
        token_number = token_number,
        status       = 'waiting'
    )
    db.session.add(new_token)
    db.session.commit()

    try:
        get_socketio().emit('queue_update', {
            'queue_id': queue_id,
            'token':    new_token.to_dict(),
            'dept':     queue.department_name
        })
    except Exception:
        pass

    if wants_json:
        position = (
            Token.query
            .filter(
                Token.queue_id == new_token.queue_id,
                Token.status   == 'waiting',
                Token.id       <  new_token.id
            )
            .count()
        )
        return jsonify({
            'success':      True,
            'token_id':     new_token.id,
            'token_number': token_number,
            'dept':         queue.department_name,
            'position':     position,
            'est_wait':     estimate_wait_minutes(new_token.queue_id, position)
        })

    flash(
        'Token ' + token_number + ' generated! Track it below.',
        'success'
    )
    return redirect(url_for('queue.my_token'))


@queue_bp.route('/cancel-token/<int:token_id>',
                methods=['POST'])
@login_required
def cancel_token(token_id):
    token = Token.query.get_or_404(token_id)
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if token.user_id != session['user_id']:
        if wants_json:
            return jsonify({'success': False, 'message': 'Unauthorized.'})
        flash('Unauthorized.', 'error')
        return redirect(url_for('queue.dashboard'))

    # Mark as cancelled
    token.status = 'cancelled'
    db.session.commit()

    # Force flush so next query sees cancelled
    db.session.expire_all()

    try:
        get_socketio().emit('token_cancelled', {
            'token_id': token_id
        })
        get_socketio().emit('queue_update', {
            'queue_id': token.queue_id
        })
    except Exception:
        pass

    if wants_json:
        return jsonify({'success': True})

    flash('Token cancelled successfully.', 'success')
    # Redirect back to dashboard — fresh load
    return redirect(url_for('queue.dashboard'))


@queue_bp.route('/live-queue')
def live_queue():
    queues = Queue.query.all()
    data   = []
    for q in queues:
        waiting = (
            Token.query
            .filter_by(queue_id=q.id, status='waiting')
            .order_by(Token.created_at)
            .all()
        )
        # NOTE: deliberately not calling q.to_dict() here — it runs
        # its own separate count() query for waiting_count, which is
        # a duplicate of the list we just fetched above. Build the
        # entry manually instead so this endpoint (polled every 15s
        # by every open tab) doesn't double its own query count.
        entry = {
            'id':              q.id,
            'hospital_id':     q.hospital_id,
            'department_name': q.department_name,
            'status':          q.status,
            'waiting_count':   len(waiting),
            'tokens':          [t.to_dict() for t in waiting],
            'est_wait_next':   estimate_wait_minutes(q.id, len(waiting))
        }
        data.append(entry)
    return jsonify(data)


@queue_bp.route('/queue-status/<int:queue_id>')
def queue_status(queue_id):
    queue   = Queue.query.get_or_404(queue_id)
    waiting = Token.query.filter_by(
        queue_id=queue_id,
        status='waiting'
    ).count()
    serving = Token.query.filter_by(
        queue_id=queue_id,
        status='serving'
    ).first()
    return jsonify({
        'queue':         queue.to_dict(),
        'waiting':       waiting,
        'est_wait':      estimate_wait_minutes(queue_id, waiting),
        'serving_token': (
            serving.token_number if serving else None
        )
    })


@queue_bp.route('/token-status')
@login_required
def token_status():
    # Always fresh query from DB
    db.session.expire_all()

    active_token = (
        Token.query
        .filter(
            Token.user_id == session['user_id'],
            Token.status.in_(['waiting', 'serving'])
        )
        .first()
    )

    if not active_token:
        return jsonify({'has_token': False})

    position = (
        Token.query
        .filter(
            Token.queue_id == active_token.queue_id,
            Token.status   == 'waiting',
            Token.id       <  active_token.id
        )
        .count()
    )

    queue = Queue.query.get(active_token.queue_id)

    return jsonify({
        'has_token':    True,
        'token_number': active_token.token_number,
        'status':       active_token.status,
        'dept':         queue.department_name if queue else '',
        'position':     position,
        'est_wait':     estimate_wait_minutes(active_token.queue_id, position),
        'token_id':     active_token.id,
        'queue_id':     active_token.queue_id
    })