import json
import os
import secrets
import time
import threading
from datetime import datetime, timedelta

import cloudinary
import cloudinary.uploader
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.database import get_db
from app.verification import get_verification_status
import config

cloudinary.config(
    cloud_name=config.CLOUDINARY_CLOUD_NAME,
    api_key=config.CLOUDINARY_API_KEY,
    api_secret=config.CLOUDINARY_API_SECRET,
)

main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_email(to_email, subject, body_html):
    if not config.RESEND_API_KEY:
        print(f"[Email не е конфигуриран] До: {to_email} | Тема: {subject}")
        return
    def _send():
        try:
            import resend
            resend.api_key = config.RESEND_API_KEY
            resend.Emails.send({
                "from": "GoodHost <onboarding@resend.dev>",
                "to": to_email,
                "subject": subject,
                "html": body_html,
            })
            print(f"[Email изпратен] До: {to_email} | Тема: {subject}")
        except Exception as e:
            print(f"[Email грешка] {e}")
    threading.Thread(target=_send, daemon=True).start()


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


def send_review_invitation_email(to_email, volunteer_name, host_name, review_link):
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#9B1C35;padding:30px;text-align:center;">
        <h1 style="color:#FBF3E4;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#9B1C35;">Оцени домакина си ⭐</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{volunteer_name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          Маркирал си посещение при <strong>{host_name}</strong>.
          Ще ни помогнеш много ако споделиш как е минало!
        </p>
        <p style="font-size:15px;color:#555;">
          Кликни по-долу за да оцениш домакина от 1 до 5 звезди и да напишеш коментар за изкарването си.
        </p>
        <div style="text-align:center;margin:30px 0;">
          <a href="{review_link}"
             style="display:inline-block;padding:14px 32px;background:#A8C256;color:#fff;
                    text-decoration:none;border-radius:6px;font-size:16px;font-weight:bold;">
            Оцени домакина
          </a>
        </div>
        <p style="font-size:12px;color:#aaa;word-break:break-all;">
          Или копирай линка: {review_link}
        </p>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(to_email, f"Оцени домакина {host_name} – GoodHost ⭐", body)


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

        photos = []
        if 'photos' in request.files:
            for f in request.files.getlist('photos')[:20]:
                if f and f.filename and allowed_file(f.filename):
                    result = cloudinary.uploader.upload(f, folder='goodhost')
                    photos.append(result['secure_url'])

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
            if 'unique' in str(e).lower():
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
            if 'unique' in str(e).lower():
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

    rating_join = '''
        SELECT h.*,
            COALESCE(AVG(r.rating), 0) as avg_rating,
            COUNT(r.id) as review_count
        FROM hosts h
        LEFT JOIN host_reviews r ON r.host_id = h.id AND r.token_used = 1 AND r.rating IS NOT NULL
    '''
    if search:
        hosts_list = db.execute(
            rating_join + ' WHERE h.name LIKE ? OR h.location LIKE ? GROUP BY h.id ORDER BY h.created_at DESC',
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        hosts_list = db.execute(
            rating_join + ' GROUP BY h.id ORDER BY h.created_at DESC'
        ).fetchall()

    visited_host_ids = set()
    if session.get('user_type') == 'volunteer':
        rows = db.execute(
            'SELECT host_id FROM host_reviews WHERE volunteer_id = ?',
            (session['user_id'],)
        ).fetchall()
        visited_host_ids = {row['host_id'] for row in rows}

    db.close()
    return render_template('hosts.html', hosts=hosts_list, search=search, visited_host_ids=visited_host_ids)


@main_bp.route('/hosts/<int:host_id>/visited', methods=['POST'])
def mark_visited(host_id):
    if 'user_id' not in session or session.get('user_type') != 'volunteer':
        flash('Трябва да влезеш като доброволец.', 'error')
        return redirect(url_for('main.login'))

    volunteer_id = session['user_id']
    db = get_db()

    existing = db.execute(
        'SELECT id FROM host_reviews WHERE volunteer_id = ? AND host_id = ?',
        (volunteer_id, host_id)
    ).fetchone()
    if existing:
        db.close()
        flash('Вече си маркирал посещение при този домакин.', 'info')
        return redirect(url_for('main.hosts'))

    host = db.execute('SELECT name FROM hosts WHERE id = ?', (host_id,)).fetchone()
    if not host:
        db.close()
        flash('Домакинът не е намерен.', 'error')
        return redirect(url_for('main.hosts'))

    volunteer = db.execute('SELECT email FROM volunteers WHERE id = ?', (volunteer_id,)).fetchone()

    token = secrets.token_urlsafe(32)
    db.execute(
        'INSERT INTO host_reviews (volunteer_id, host_id, review_token) VALUES (?, ?, ?)',
        (volunteer_id, host_id, token)
    )
    db.commit()
    db.close()

    review_link = url_for('main.review_host', token=token, _external=True)
    send_review_invitation_email(volunteer['email'], session['user_name'], host['name'], review_link)

    flash(f'Изпратихме ти имейл с линк за оценка на {host["name"]}!', 'success')
    return redirect(url_for('main.hosts'))


@main_bp.route('/review/<token>', methods=['GET', 'POST'])
def review_host(token):
    db = get_db()
    review = db.execute(
        '''SELECT r.*, h.name as host_name, v.name as volunteer_name
           FROM host_reviews r
           JOIN hosts h ON h.id = r.host_id
           JOIN volunteers v ON v.id = r.volunteer_id
           WHERE r.review_token = ?''',
        (token,)
    ).fetchone()

    if not review:
        db.close()
        flash('Линкът е невалиден.', 'error')
        return redirect(url_for('main.hosts'))

    if review['token_used']:
        db.close()
        flash('Тази оценка вече е подадена.', 'info')
        return redirect(url_for('main.hosts'))

    if request.method == 'POST':
        rating = request.form.get('rating', '')
        comment = request.form.get('comment', '').strip()

        if not rating.isdigit() or not (1 <= int(rating) <= 5):
            db.close()
            flash('Моля избери оценка от 1 до 5 звезди.', 'error')
            return render_template('review.html', review=review, token=token)

        db.execute(
            'UPDATE host_reviews SET rating = ?, comment = ?, token_used = 1 WHERE review_token = ?',
            (int(rating), comment, token)
        )
        db.commit()
        db.close()
        flash(f'Благодарим ти за оценката на {review["host_name"]}! 🌟', 'success')
        return redirect(url_for('main.hosts'))

    db.close()
    return render_template('review.html', review=review, token=token)


@main_bp.route('/hosts/<int:host_id>/photos/add', methods=['POST'])
def add_photos(host_id):
    if 'user_id' not in session or session.get('user_type') != 'host' or session['user_id'] != host_id:
        return redirect(url_for('main.profile'))

    db = get_db()
    host = db.execute('SELECT photos FROM hosts WHERE id = ?', (host_id,)).fetchone()
    photos = json.loads(host['photos'] or '[]')

    added = 0
    for f in request.files.getlist('photos'):
        if len(photos) >= 20:
            break
        if f and f.filename and allowed_file(f.filename):
            result = cloudinary.uploader.upload(f, folder='goodhost')
            photos.append(result['secure_url'])
            added += 1

    db.execute('UPDATE hosts SET photos = ? WHERE id = ?', (json.dumps(photos), host_id))
    db.commit()
    db.close()

    if added:
        flash(f'Добавени {added} нови снимки.', 'success')
    else:
        flash('Не са добавени снимки. Провери формата или лимита от 20 снимки.', 'error')
    return redirect(url_for('main.profile'))


@main_bp.route('/hosts/<int:host_id>/photos/delete', methods=['POST'])
def delete_photo(host_id):
    if 'user_id' not in session or session.get('user_type') != 'host' or session['user_id'] != host_id:
        return redirect(url_for('main.profile'))

    photo_url = request.form.get('filename', '').strip()
    if not photo_url:
        flash('Невалидна снимка.', 'error')
        return redirect(url_for('main.profile'))

    db = get_db()
    host = db.execute('SELECT photos FROM hosts WHERE id = ?', (host_id,)).fetchone()
    photos = json.loads(host['photos'] or '[]')

    if photo_url in photos:
        photos.remove(photo_url)
        db.execute('UPDATE hosts SET photos = ? WHERE id = ?', (json.dumps(photos), host_id))
        db.commit()
        # Изтриване от Cloudinary по public_id
        try:
            # URL формат: .../goodhost/PUBLIC_ID.ext
            public_id = 'goodhost/' + photo_url.split('/')[-1].rsplit('.', 1)[0]
            cloudinary.uploader.destroy(public_id)
        except Exception:
            pass
        flash('Снимката беше изтрита.', 'success')
    else:
        flash('Снимката не е намерена.', 'error')

    db.close()
    return redirect(url_for('main.profile'))


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
        user = db.execute('SELECT * FROM hosts WHERE email = ?', (email,)).fetchone()
        user_type = 'host'
        if not user:
            user = db.execute('SELECT * FROM volunteers WHERE email = ?', (email,)).fetchone()
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

    expires_at = record['expires_at']
    if isinstance(expires_at, str):
        expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
    if expires_at < datetime.now():
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
