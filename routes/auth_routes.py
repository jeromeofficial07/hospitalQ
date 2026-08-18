# routes/auth_routes.py
from flask import (Blueprint, request, session,
                   redirect, url_for,
                   render_template, flash)
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from models.user_model import User
from models.otp_model  import PasswordResetOTP
from db import db

auth_bp = Blueprint('auth', __name__)

OTP_EXPIRY_MINUTES  = 10
OTP_RESEND_COOLDOWN = 60   # seconds between requesting new codes
MAX_OTP_ATTEMPTS    = 5    # wrong-code attempts before a code is locked out


@auth_bp.route('/')
def index():
    return render_template('index.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Public patient registration only. This can NEVER create an admin
    account — role is hardcoded server-side regardless of what's
    posted, so no form field, hidden input, or raw POST request can
    self-elevate to admin. Admin accounts are only created by an
    already-authenticated admin, from /admin/create-admin.
    """
    if request.method == 'POST':
        name     = request.form.get('name',     '').strip()
        email    = request.form.get('email',    '').strip()
        phone    = request.form.get('phone',    '').strip() or None
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))

        if phone and User.query.filter_by(phone=phone).first():
            flash('That mobile number is already registered.', 'error')
            return redirect(url_for('auth.register'))

        user = User(name=name, email=email, phone=phone, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login only. Admins use /admin/login."""
    if request.method == 'POST':
        email    = request.form.get('email',    '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(
            email=email, role='user'
        ).first()

        if user and user.check_password(password):
            session['user_id']   = user.id
            session['user_name'] = user.name
            session['role']      = user.role
            return redirect(url_for('queue.dashboard'))

        flash('Invalid email or password.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login only. Separate page from the user login."""
    if request.method == 'POST':
        email    = request.form.get('email',    '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(
            email=email, role='admin'
        ).first()

        if user and user.check_password(password):
            session['user_id']   = user.id
            session['user_name'] = user.name
            session['role']      = user.role
            return redirect(url_for('admin.dashboard'))

        flash('Invalid admin email or password.', 'error')
        return redirect(url_for('auth.admin_login'))

    return render_template('admin_login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


# ── FORGOT PASSWORD ──

def send_email_otp(to_email, otp_code, user_name):
    """
    Sends the OTP over Gmail SMTP using MAIL_USERNAME/MAIL_PASSWORD
    from config (a Gmail App Password, see config.py for setup).
    Falls back to logging the code to the console if SMTP isn't
    configured yet, so the flow stays testable without real creds.
    """
    import smtplib
    from email.mime.text import MIMEText
    from flask import current_app

    sender   = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')

    if not sender or not password:
        current_app.logger.warning(
            f"[DEV — email not configured] OTP for {to_email}: {otp_code}"
        )
        return False

    msg = MIMEText(
        f"Hi {user_name},\n\n"
        f"Your QueueFlow password reset code is: {otp_code}\n"
        f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )
    msg['Subject'] = 'Your QueueFlow Password Reset Code'
    msg['From']    = sender
    msg['To']      = to_email

    try:
        with smtplib.SMTP(
            current_app.config.get('MAIL_SERVER', 'smtp.gmail.com'),
            current_app.config.get('MAIL_PORT', 587)
        ) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [to_email], msg.as_string())
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send OTP email: {e}")
        return False


def send_sms_otp(to_phone, otp_code, user_name):
    """
    STUB — no SMS provider is wired up yet. Plug in Twilio (or any
    provider) here once you have an account. Example, using the
    TWILIO_* settings already scaffolded in config.py:

        from twilio.rest import Client
        from flask import current_app
        client = Client(
            current_app.config['TWILIO_ACCOUNT_SID'],
            current_app.config['TWILIO_AUTH_TOKEN']
        )
        client.messages.create(
            body=f"Your QueueFlow reset code is {otp_code}",
            from_=current_app.config['TWILIO_FROM_NUMBER'],
            to=to_phone
        )

    Until then, this just logs the code so you can still test the
    full reset flow end-to-end locally.
    """
    from flask import current_app
    current_app.logger.warning(
        f"[DEV — SMS not configured] OTP for {to_phone}: {otp_code}"
    )
    return False


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        method     = request.form.get('method', 'email')  # 'email' or 'sms'

        # Same message either way, regardless of whether an account
        # actually matched — otherwise this endpoint becomes a way to
        # check which emails/phone numbers are registered.
        generic_msg = (
            'If an account matches that information, a verification '
            'code has been sent.'
        )

        if not identifier:
            flash('Please enter your email or mobile number.', 'error')
            return redirect(url_for('auth.forgot_password'))

        user = None
        if '@' in identifier:
            user = User.query.filter_by(email=identifier).first()
        else:
            user = User.query.filter_by(phone=identifier).first()

        if user:
            # Cooldown: don't let someone spam-generate codes
            recent = (
                PasswordResetOTP.query
                .filter_by(user_id=user.id)
                .order_by(PasswordResetOTP.created_at.desc())
                .first()
            )
            if recent and (datetime.utcnow() - recent.created_at).total_seconds() < OTP_RESEND_COOLDOWN:
                flash(
                    'A code was already sent recently — please wait a '
                    'moment before requesting another.',
                    'warning'
                )
                session['reset_user_id'] = user.id
                return redirect(url_for('auth.verify_otp'))

            # Invalidate any older unused codes for this user first
            PasswordResetOTP.query.filter_by(
                user_id=user.id, used=False
            ).update({'used': True})

            code = PasswordResetOTP.generate_code()
            otp = PasswordResetOTP(
                user_id=user.id,
                otp_hash=generate_password_hash(code),
                channel=method,
                expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
            )
            db.session.add(otp)
            db.session.commit()

            if method == 'sms' and user.phone:
                send_sms_otp(user.phone, code, user.name)
            else:
                send_email_otp(user.email, code, user.name)

            session['reset_user_id'] = user.id

        flash(generic_msg, 'success')
        return redirect(url_for('auth.verify_otp'))

    return render_template('forgot_password.html')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_user_id' not in session:
        flash('Please request a reset code first.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        code              = request.form.get('otp', '').strip()
        new_password      = request.form.get('password', '').strip()
        confirm_password  = request.form.get('confirm_password', '').strip()
        user_id           = session.get('reset_user_id')

        otp_record = (
            PasswordResetOTP.query
            .filter_by(user_id=user_id, used=False)
            .order_by(PasswordResetOTP.created_at.desc())
            .first()
        )

        if not otp_record or otp_record.expires_at < datetime.utcnow():
            flash('That code has expired. Please request a new one.', 'error')
            session.pop('reset_user_id', None)
            return redirect(url_for('auth.forgot_password'))

        if otp_record.attempts >= MAX_OTP_ATTEMPTS:
            otp_record.used = True
            db.session.commit()
            flash('Too many incorrect attempts. Please request a new code.', 'error')
            session.pop('reset_user_id', None)
            return redirect(url_for('auth.forgot_password'))

        if not check_password_hash(otp_record.otp_hash, code):
            otp_record.attempts += 1
            db.session.commit()
            flash('Incorrect code. Please try again.', 'error')
            return render_template('verify_otp.html')

        if not new_password or len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('verify_otp.html')

        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('verify_otp.html')

        user = User.query.get(user_id)
        user.set_password(new_password)
        otp_record.used = True
        db.session.commit()

        session.pop('reset_user_id', None)

        flash('Password reset successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('verify_otp.html')