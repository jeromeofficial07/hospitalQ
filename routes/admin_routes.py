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
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


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
    serving = Token.query.filter_by(
        queue_id=queue_id, status='serving'
    ).first()
    if serving:
        serving.status = 'completed'
        db.session.commit()

    nxt = (
        Token.query
        .filter_by(queue_id=queue_id, status='waiting')
        .order_by(Token.created_at)
        .first()
    )
    if nxt:
        nxt.status = 'serving'
        db.session.commit()
        try:
            get_socketio().emit('next_token', {
                'token_number': nxt.token_number,
                'queue_id':     queue_id,
                'user_id':      nxt.user_id
            })
            # Emit full queue refresh
            get_socketio().emit('queue_update', {
                'queue_id': queue_id
            })
        except Exception:
            pass
        return jsonify({'success': True, 'token': nxt.to_dict()})
    return jsonify({'success': False, 'message': 'Queue is empty'})


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
    queues = Queue.query.all()
    data   = []
    for q in queues:
        waiting = Token.query.filter_by(
            queue_id=q.id, status='waiting'
        ).count()
        serving = Token.query.filter_by(
            queue_id=q.id, status='serving'
        ).first()
        data.append({
            'id':              q.id,
            'department_name': q.department_name,
            'status':          q.status,
            'waiting_count':   waiting,
            'serving_token':   serving.token_number if serving else None
        })
    return jsonify(data)


@admin_bp.route('/token-list')
@admin_required
def token_list():
    tokens = (
        Token.query
        .order_by(Token.created_at.desc())
        .limit(20).all()
    )
    data = []
    for t in tokens:
        data.append({
            'id':            t.id,
            'token_number':  t.token_number,
            'status':        t.status,
            'user_name':     t.user.name,
            'dept_name':     t.queue.department_name,
            'created_at':    t.created_at.strftime('%H:%M:%S'),
            'est_wait':      '~5 min'
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
    try:
        dept_stats = (
            db.session.query(
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
            .group_by(Queue.department_name)
            .all()
        )
        return jsonify([{
            'dept':      d.department_name,
            'total':     d.total,
            'completed': int(d.done      or 0),
            'cancelled': int(d.cancelled or 0)
        } for d in dept_stats])
    except Exception:
        return jsonify([])
