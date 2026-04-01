import json
import os
import secrets
import time
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.database import get_db
from app.verification import get_verification_status
import config

main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_email(to_email, subject, body_html):
    if not config.MAIL_USERNAME or not config.MAIL_PASSWORD:
        print(f"[Email не е конфигуриран] До: {to_email} | Тема: {subject}")
        return
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"GoodHost <{config.MAIL_USERNAME}>"
        msg['To'] = to_email
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        with smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
            server.sendmail(config.MAIL_USERNAME, to_email, msg.as_string())
        print(f"[Email изпратен] До: {to_email} | Тема: {subject}")
    except Exception as e:
        print(f"[Email грешка] {e}")


def send_registration_email(to_email, name, user_type):
    role = "домакин" if user_type == "host" else "доброволец"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#2e7d32;padding:30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#2e7d32;">Добре дошъл, {name}! 🎉</h2>
        <p style="font-size:16px;color:#333;">
          Регистрацията ти като <strong>{role}</strong> в платформата GoodHost беше успешна.
        </p>
        <p style="font-size:15px;color:#555;">
          Вече можеш да влезеш в профила си и да се свържеш с общността ни.
        </p>
        <div style="text-align:center;margin:30px 0;">
          <a href="http://localhost:5000/login"
             style="display:inline-block;padding:14px 32px;background:#2e7d32;color:#fff;
                    text-decoration:none;border-radius:6px;font-size:16px;font-weight:bold;">
            Влез в профила
          </a>
        </div>
        <p style="font-size:14px;color:#888;">
          Ако не си се регистрирал ти, просто игнорирай този имейл.
        </p>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(to_email, "Добре дошъл в GoodHost! ✅", body)


def send_login_email(to_email, name):
    now = datetime.now().strftime("%d.%m.%Y в %H:%M")
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#1565c0;padding:30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#1565c0;">Нов вход в профила ти</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          Засечен е нов вход в твоя профил в GoodHost на <strong>{now}</strong>.
        </p>
        <p style="font-size:15px;color:#e53935;">
          Ако не си бил ти, смени паролата си незабавно.
        </p>
        <div style="text-align:center;margin:25px 0;">
          <a href="http://localhost:5000/forgot-password"
             style="display:inline-block;padding:12px 28px;background:#e53935;color:#fff;
                    text-decoration:none;border-radius:6px;font-size:15px;font-weight:bold;">
            Смени паролата
          </a>
        </div>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(to_email, "Нов вход в профила ти – GoodHost 🔐", body)


def send_forgot_password_email(to_email, name, reset_link):
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#2e7d32;padding:30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#2e7d32;">Смяна на парола</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          Получихме заявка за смяна на паролата ти в GoodHost.
          Кликни на бутона по-долу за да зададеш нова парола.
        </p>
        <p style="font-size:14px;color:#e53935;">
          Линкът е валиден <strong>1 час</strong>. Ако не си поискал смяна на парола, игнорирай този имейл.
        </p>
        <div style="text-align:center;margin:30px 0;">
          <a href="{reset_link}"
             style="display:inline-block;padding:14px 32px;background:#2e7d32;color:#fff;
                    text-decoration:none;border-radius:6px;font-size:16px;font-weight:bold;">
            Смени паролата
          </a>
        </div>
        <p style="font-size:12px;color:#aaa;word-break:break-all;">
          Или копирай линка: {reset_link}
        </p>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(to_email, "Смяна на парола – GoodHost 🔑", body)


@main_bp.context_processor
def inject_session():
    return dict(
        is_logged_in='user_id' in session,
        current_user_id=session.get('user_id'),
        current_user_name=session.get('user_name', ''),
        current_user_type=session.get('user_type', ''),
    )


@main_bp.app_template_filter('from_json')
def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except Exception:
            return []
    return []


@main_bp.route('/')
def index():
    return render_template('homepage.html')


@main_bp.route('/registration')
def registration():
    return render_template('registration.html')


@main_bp.route('/hostsregistration', methods=['GET', 'POST'])
def hostsregistration():
    if request.method == 'POST':
        name             = request.form.get('name', '').strip()
        age              = request.form.get('age', '0')
        email            = request.form.get('email', '').strip().lower()
        phone            = request.form.get('phone', '').strip()
        city             = request.form.get('city', '').strip()
        region           = request.form.get('region', '').strip()
        about            = request.form.get('about', '').strip()
        password         = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if password != password_confirm:
            flash('Паролите не съвпадат.', 'error')
            return render_template('hostsregistration.html')
        if len(password) < 6:
            flash('Паролата трябва да е поне 6 символа.', 'error')
            return render_template('hostsregistration.html')

        location      = f"{city}, {region}" if region else city
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        photos = []
        if 'photos' in request.files:
            for f in request.files.getlist('photos')[:20]:
                if f and f.filename and allowed_file(f.filename):
                    filename = f"{int(time.time())}_{secure_filename(f.filename)}"
                    f.save(os.path.join(upload_folder, filename))
                    photos.append(filename)

        max_guests = int(request.form.get('max_guests', 1) or 1)

        db = get_db()
        try:
            cursor = db.execute(
                '''INSERT INTO hosts (name, age, bio, email, phone, location, max_guests, password_hash, photos)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, int(age), about, email, phone, location, max_guests, password_hash, json.dumps(photos))
            )
            host_id = cursor.lastrowid
            db.commit()
        except Exception as e:
            db.close()
            if 'UNIQUE' in str(e):
                flash('Този имейл вече е регистриран.', 'error')
            else:
                flash('Грешка при регистрацията. Опитай отново.', 'error')
            return render_template('hostsregistration.html')
        db.close()

        send_registration_email(email, name, 'host')
        return redirect(url_for('verify.verify_page', user_type='host', user_id=host_id))

    return render_template('hostsregistration.html')


@main_bp.route('/register/volunteer', methods=['GET', 'POST'])
def volunteer_registration():
    if request.method == 'POST':
        name             = request.form.get('name', '').strip()
        age              = request.form.get('age', '0')
        email            = request.form.get('email', '').strip().lower()
        phone            = request.form.get('phone', '').strip()
        password         = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if password != password_confirm:
            flash('Паролите не съвпадат.', 'error')
            return render_template('volunteer_registration.html')
        if len(password) < 6:
            flash('Паролата трябва да е поне 6 символа.', 'error')
            return render_template('volunteer_registration.html')

        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO volunteers (name, age, email, phone, password_hash) VALUES (?, ?, ?, ?, ?)',
                (name, int(age), email, phone, password_hash)
            )
            volunteer_id = cursor.lastrowid
            db.commit()
        except Exception as e:
            db.close()
            if 'UNIQUE' in str(e):
                flash('Този имейл вече е регистриран.', 'error')
            else:
                flash('Грешка при регистрацията. Опитай отново.', 'error')
            return render_template('volunteer_registration.html')
        db.close()

        send_registration_email(email, name, 'volunteer')
        return redirect(url_for('verify.verify_page', user_type='volunteer', user_id=volunteer_id))

    return render_template('volunteer_registration.html')


@main_bp.route('/hosts')
def hosts():
    search = request.args.get('search', '').strip()
    db = get_db()
    if search:
        hosts_list = db.execute(
            'SELECT * FROM hosts WHERE name LIKE ? OR location LIKE ? ORDER BY created_at DESC',
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        hosts_list = db.execute('SELECT * FROM hosts ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('hosts.html', hosts=hosts_list, search=search)


@main_bp.route('/hosts/<int:host_id>/delete', methods=['POST'])
def delete_host(host_id):
    if 'user_id' not in session or session.get('user_type') != 'host':
        return redirect(url_for('main.login'))
    if session['user_id'] != host_id:
        return redirect(url_for('main.hosts'))
    db = get_db()
    db.execute('DELETE FROM hosts WHERE id = ?', (host_id,))
    db.commit()
    db.close()
    session.clear()
    flash('Профилът ти беше изтрит успешно.', 'success')
    return redirect(url_for('main.index'))


@main_bp.route('/rules')
def rules():
    return render_template('rules.html')


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('main.profile'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        user      = db.execute('SELECT * FROM hosts WHERE email = ?', (email,)).fetchone()
        user_type = 'host'
        if not user:
            user      = db.execute('SELECT * FROM volunteers WHERE email = ?', (email,)).fetchone()
            user_type = 'volunteer'
        db.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id']   = user['id']
            session['user_type'] = user_type
            session['user_name'] = user['name']
            send_login_email(email, user['name'])
            return redirect(url_for('main.profile'))
        else:
            flash('Грешен имейл или парола.', 'error')

    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))


@main_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Трябва да влезеш в профила си.', 'error')
        return redirect(url_for('main.login'))

    current_user_type = session.get('user_type')
    current_user_id = session.get('user_id')

    db = get_db()
    if current_user_type == 'host':
        user = db.execute('SELECT * FROM hosts WHERE id = ?', (current_user_id,)).fetchone()
    else:
        user = db.execute('SELECT * FROM volunteers WHERE id = ?', (current_user_id,)).fetchone()
    db.close()

    is_verified = bool(user['id_verified']) if user and 'id_verified' in user.keys() else False
    if user and not is_verified:
        try:
            status = get_verification_status(current_user_type, current_user_id)
            is_verified = bool(status.get('verified', False))
        except Exception:
            pass
    verification_url = url_for('verify.verify_page', user_type=current_user_type, user_id=current_user_id)

    return render_template(
        'profile.html',
        user=user,
        is_verified=is_verified,
        verification_url=verification_url,
        stripe_publishable_key=config.STRIPE_PUBLISHABLE_KEY
    )


@main_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        db = get_db()
        user = db.execute('SELECT *, "host" as utype FROM hosts WHERE email = ?', (email,)).fetchone()
        user_type = 'host'
        if not user:
            user = db.execute('SELECT *, "volunteer" as utype FROM volunteers WHERE email = ?', (email,)).fetchone()
            user_type = 'volunteer'

        if user:
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            db.execute(
                'INSERT INTO password_reset_tokens (email, user_type, token, expires_at) VALUES (?, ?, ?, ?)',
                (email, user_type, token, expires_at)
            )
            db.commit()
            reset_link = url_for('main.reset_password', token=token, _external=True)
            send_forgot_password_email(email, user['name'], reset_link)

        db.close()
        flash('Ако имейлът е регистриран, ще получиш линк за смяна на парола.', 'success')
        return redirect(url_for('main.forgot_password'))

    return render_template('forgot_password.html')


@main_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    db = get_db()
    record = db.execute(
        'SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0',
        (token,)
    ).fetchone()

    if not record:
        db.close()
        flash('Линкът е невалиден или вече е използван.', 'error')
        return redirect(url_for('main.forgot_password'))

    if datetime.strptime(record['expires_at'], '%Y-%m-%d %H:%M:%S') < datetime.now():
        db.close()
        flash('Линкът е изтекъл. Поискай нов.', 'error')
        return redirect(url_for('main.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if password != password_confirm:
            flash('Паролите не съвпадат.', 'error')
            return render_template('reset_password.html', token=token)
        if len(password) < 6:
            flash('Паролата трябва да е поне 6 символа.', 'error')
            return render_template('reset_password.html', token=token)

        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        table = 'hosts' if record['user_type'] == 'host' else 'volunteers'
        db.execute(f'UPDATE {table} SET password_hash = ? WHERE email = ?',
                   (password_hash, record['email']))
        db.execute('UPDATE password_reset_tokens SET used = 1 WHERE token = ?', (token,))
        db.commit()
        db.close()
        flash('Паролата беше сменена успешно! Можеш да влезеш.', 'success')
        return redirect(url_for('main.login'))

    db.close()
    return render_template('reset_password.html', token=token)
