# routes/queue_routes.py
from flask import (Blueprint, request, session,
                   redirect, url_for, render_template,
                   jsonify, flash)
from functools import wraps
from models.token_model import Token
from models.queue_model  import Queue
from db import db

queue_bp = Blueprint('queue', __name__)

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
        est_wait = position * 5

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
        flash(
            'You already have active token '
            + existing.token_number
            + '. Please cancel it first.',
            'warning'
        )
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

    if token.user_id != session['user_id']:
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
        entry           = q.to_dict()
        entry['tokens'] = [t.to_dict() for t in waiting]
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
        'est_wait':      waiting * 5,
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
        'est_wait':     position * 5,
        'token_id':     active_token.id,
        'queue_id':     active_token.queue_id
    })