# routes/auth_routes.py
from flask import (Blueprint, request, session,
                   redirect, url_for,
                   render_template, flash)
from models.user_model import User
from db import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return render_template('index.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form.get('name',     '').strip()
        email    = request.form.get('email',    '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role',     'user')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email',    '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role',     'user')

        user = User.query.filter_by(
            email=email, role=role
        ).first()

        if user and user.check_password(password):
            session['user_id']   = user.id
            session['user_name'] = user.name
            session['role']      = user.role

            if user.role == 'admin':
                # FIX — correct admin redirect
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('queue.dashboard'))

        flash('Invalid email or password.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))