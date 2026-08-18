# routes/admin_routes.py
from flask import (Blueprint, session, redirect,
                   url_for, render_template,
                   jsonify, request, flash)
from functools import wraps
from models.token_model import Token
from models.queue_model  import Queue
from models.user_model   import User
from db import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_socketio():
    from app import socketio
    return socketio

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/create-admin', methods=['POST'])
@admin_required
def create_admin():
    """
    The ONLY way a new admin account can be created. Requires an
    already-authenticated admin session (admin_required), plus that
    admin re-entering their own password as a lightweight step-up
    check before minting a new privileged account.
    """
    data = request.get_json(silent=True) or {}
    name             = (data.get('name')             or '').strip()
    email            = (data.get('email')            or '').strip()
    password         = (data.get('password')         or '').strip()
    confirm_password = (data.get('confirm_password') or '').strip()

    if not name or not email or not password or not confirm_password:
        return jsonify({'success': False, 'message': 'All fields are required.'})

    if len(password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'})

    acting_admin = User.query.get(session.get('user_id'))
    if not acting_admin or not acting_admin.check_password(confirm_password):
        return jsonify({'success': False, 'message': 'Your password confirmation was incorrect.'})

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'That email is already registered.'})

    new_admin = User(name=name, email=email, role='admin')
    new_admin.set_password(password)
    db.session.add(new_admin)
    db.session.commit()

    return jsonify({'success': True, 'name': new_admin.name})


@admin_bp.route('/staff-list')
@admin_required
def staff_list():
    admins = (
        User.query
        .filter_by(role='admin')
        .order_by(User.created_at.desc())
        .all()
    )
    return jsonify([
        {
            'name':       a.name,
            'email':      a.email,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else ''
        }
        for a in admins
    ])


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    queues = Queue.query.all()
    if not queues:
        defaults = ['Banking','Pharmacy','Immigration','Medical']
        for dept in defaults:
            q = Queue(department_name=dept, status='active')
            db.session.add(q)
        db.session.commit()
        queues = Queue.query.all()

    total_tokens  = Token.query.count()
    waiting       = Token.query.filter_by(status='waiting').count()
    completed     = Token.query.filter_by(status='completed').count()
    cancelled     = Token.query.filter_by(status='cancelled').count()
    recent_tokens = (
        Token.query
        .order_by(Token.created_at.desc())
        .limit(20).all()
    )
    return render_template(
        'admin.html',
        queues    = queues,
        total     = total_tokens,
        waiting   = waiting,
        completed = completed,
        cancelled = cancelled,
        tokens    = recent_tokens
    )


@admin_bp.route('/next-token/<int:queue_id>', methods=['POST'])
@admin_required
def next_token(queue_id):
    from queue_engine import advance_queue

    nxt = advance_queue(queue_id)
    if nxt:
        return jsonify({'success': True, 'token': nxt.to_dict()})
    return jsonify({'success': False, 'message': 'Queue is empty'})


@admin_bp.route('/no-show/<int:queue_id>', methods=['POST'])
@admin_required
def no_show(queue_id):
    """
    Admin clicks 'No Show' on whoever is currently being served in
    this queue. First couple of misses send them to the back of the
    line; the third cancels the token. Either way the queue advances
    to whoever's next.
    """
    from queue_engine import mark_no_show

    result = mark_no_show(queue_id, reason='manual')
    if result:
        return jsonify({'success': True, **result})
    return jsonify({
        'success': False,
        'message': 'No token is currently being served in this queue'
    })


@admin_bp.route('/pause-queue/<int:queue_id>', methods=['POST'])
@admin_required
def pause_queue(queue_id):
    queue = Queue.query.get_or_404(queue_id)
    queue.status = 'paused' if queue.status == 'active' else 'active'
    db.session.commit()
    try:
        # Emit status change with full details
        get_socketio().emit('queue_status_changed', {
            'queue_id': queue_id,
            'status':   queue.status,
            'dept':     queue.department_name
        })
    except Exception:
        pass
    return jsonify({
        'success': True,
        'status':  queue.status,
        'queue_id': queue_id
    })


@admin_bp.route('/close-queue/<int:queue_id>', methods=['POST'])
@admin_required
def close_queue(queue_id):
    queue = Queue.query.get_or_404(queue_id)
    queue.status = 'closed'
    db.session.commit()
    try:
        # Emit close event with full details
        get_socketio().emit('queue_status_changed', {
            'queue_id': queue_id,
            'status':   'closed',
            'dept':     queue.department_name
        })
    except Exception:
        pass
    return jsonify({
        'success':  True,
        'queue_id': queue_id,
        'status':   'closed'
    })


@admin_bp.route('/queue-list')
@admin_required
def queue_list():
    from sqlalchemy import func

    queues = Queue.query.all()

    # ONE aggregate query for every department's waiting count,
    # instead of a separate count() per department.
    waiting_counts = dict(
        db.session.query(Token.queue_id, func.count(Token.id))
        .filter(Token.status == 'waiting')
        .group_by(Token.queue_id)
        .all()
    )

    # ONE query for every currently-serving token, instead of a
    # separate lookup per department.
    serving_tokens = {
        t.queue_id: t.token_number
        for t in Token.query.filter_by(status='serving').all()
    }

    data = [
        {
            'id':              q.id,
            'department_name': q.department_name,
            'status':          q.status,
            'waiting_count':   waiting_counts.get(q.id, 0),
            'serving_token':   serving_tokens.get(q.id)
        }
        for q in queues
    ]
    return jsonify(data)


@admin_bp.route('/token-list')
@admin_required
def token_list():
    from sqlalchemy.orm import joinedload
    from routes.queue_routes import estimate_wait_minutes

    # joinedload pulls user + queue in the SAME query via a SQL JOIN,
    # instead of the old behavior where t.user.name and
    # t.queue.department_name each triggered their own lazy-load
    # query per row — up to 40 extra queries for 20 tokens.
    tokens = (
        Token.query
        .options(joinedload(Token.user), joinedload(Token.queue))
        .order_by(Token.created_at.desc())
        .limit(20)
        .all()
    )

    # Position ("how many people are ahead of this one") used to be
    # a separate count() query per waiting token. Instead, fetch
    # every relevant queue's full waiting list ONCE and compute each
    # token's position from that in Python.
    queue_ids = {t.queue_id for t in tokens if t.status == 'waiting'}
    waiting_order_by_queue = {}
    if queue_ids:
        all_waiting = (
            Token.query
            .filter(Token.queue_id.in_(queue_ids), Token.status == 'waiting')
            .order_by(Token.queue_id, Token.created_at)
            .all()
        )
        for tok in all_waiting:
            waiting_order_by_queue.setdefault(tok.queue_id, []).append(tok.id)

    data = []
    for t in tokens:
        if t.status == 'waiting':
            ordered_ids = waiting_order_by_queue.get(t.queue_id, [])
            position = ordered_ids.index(t.id) if t.id in ordered_ids else 0
            est_wait = f"~{estimate_wait_minutes(t.queue_id, position)} min"
        else:
            est_wait = '—'

        data.append({
            'id':            t.id,
            'token_number':  t.token_number,
            'status':        t.status,
            'user_name':     t.user.name,
            'dept_name':     t.queue.department_name,
            'created_at':    t.created_at.strftime('%H:%M:%S'),
            'est_wait':      est_wait
        })
    return jsonify(data)


@admin_bp.route('/stats')
@admin_required
def stats():
    total     = Token.query.count()
    waiting   = Token.query.filter_by(status='waiting').count()
    completed = Token.query.filter_by(status='completed').count()
    cancelled = Token.query.filter_by(status='cancelled').count()
    return jsonify({
        'total':     total,
        'waiting':   waiting,
        'completed': completed,
        'cancelled': cancelled
    })


@admin_bp.route('/analytics')
@admin_required
def analytics():
    from sqlalchemy import func, case
    from routes.queue_routes import get_avg_service_seconds

    try:
        dept_stats = (
            db.session.query(
                Queue.id,
                Queue.department_name,
                func.count(Token.id).label('total'),
                func.sum(
                    case((Token.status == 'completed', 1), else_=0)
                ).label('done'),
                func.sum(
                    case((Token.status == 'cancelled', 1), else_=0)
                ).label('cancelled')
            )
            .join(Token, Queue.id == Token.queue_id)
            .group_by(Queue.id, Queue.department_name)
            .all()
        )
        return jsonify([{
            'dept':          d.department_name,
            'total':         d.total,
            'completed':     int(d.done      or 0),
            'cancelled':     int(d.cancelled or 0),
            # NEW: real average service time per department, in minutes,
            # driven by the same historical called_at/completed_at data
            # that powers the live wait-time estimates.
            'avg_wait_min':  round(get_avg_service_seconds(d.id) / 60, 1)
        } for d in dept_stats])
    except Exception:
        return jsonify([])


@admin_bp.route('/peak-hours')
@admin_required
def peak_hours():
    """
    Tokens generated per hour of day, across all history, to reveal
    when the hospital actually gets busy — 24 buckets, hour 0-23.
    """
    from sqlalchemy import func

    try:
        rows = (
            db.session.query(
                func.strftime('%H', Token.created_at).label('hour'),
                func.count(Token.id).label('count')
            )
            .group_by('hour')
            .all()
        )
        counts_by_hour = {int(r.hour): r.count for r in rows if r.hour is not None}
        data = [
            {'hour': h, 'count': counts_by_hour.get(h, 0)}
            for h in range(24)
        ]
        return jsonify(data)
    except Exception:
        return jsonify([])