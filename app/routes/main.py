import json
import os
import secrets
import time
import threading
from datetime import datetime, timedelta, date as date_type

import cloudinary
import cloudinary.uploader
from groq import Groq
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
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
                "from": "GoodHost <noreply@goodhost.website>",
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


def send_plan_visit_email(to_email, volunteer_name, host_name, display_date, display_date_to=None):
    period = f"от <strong>{display_date}</strong> до <strong>{display_date_to}</strong>" if display_date_to and display_date_to != display_date else f"на <strong>{display_date}</strong>"
    subject_date = f"{display_date}–{display_date_to}" if display_date_to and display_date_to != display_date else display_date
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#9B1C35;padding:30px;text-align:center;">
        <h1 style="color:#FBF3E4;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#9B1C35;">Планирано посещение 📅</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{volunteer_name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          Маркирал си планирано посещение при <strong>{host_name}</strong> {period}.
        </p>
        <p style="font-size:15px;color:#555;">
          След като ги посетиш, не забравяй да оставиш отзив — помага на другите доброволци да изберат добре!
        </p>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(to_email, f"Планирано посещение при {host_name} на {subject_date} – GoodHost 📅", body)


def send_review_invitation_email(to_email, volunteer_name, host_name, review_link, from_date='', to_date=''):
    if from_date and to_date and from_date != to_date:
        visit_info = f"от <strong>{from_date}</strong> до <strong>{to_date}</strong>"
    elif from_date:
        visit_info = f"на <strong>{from_date}</strong>"
    else:
        visit_info = ''
    visit_sentence = f"Маркирал си посещение при <strong>{host_name}</strong>{' ' + visit_info if visit_info else ''}."
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#9B1C35;padding:30px;text-align:center;">
        <h1 style="color:#FBF3E4;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#9B1C35;">Оцени домакина си ⭐</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{volunteer_name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          {visit_sentence}
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


def send_visit_request_email(host_email, host_name, volunteer_name, from_date, to_date, message, profile_url, num_guests=1):
    period = f"от <strong>{from_date}</strong> до <strong>{to_date}</strong>" if from_date != to_date else f"на <strong>{from_date}</strong>"
    guests_line = f'<p style="font-size:15px;color:#555;">Брой гости: <strong>{num_guests}</strong></p>'
    message_block = f'<p style="font-size:15px;color:#555;background:#f9f3e8;border-left:3px solid #A8C256;padding:0.6em 1em;border-radius:4px;">{message}</p>' if message else ''
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#9B1C35;padding:30px;text-align:center;">
        <h1 style="color:#FBF3E4;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#9B1C35;">Нова заявка за посещение 📬</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{host_name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          Доброволецът <strong>{volunteer_name}</strong> иска да те посети {period}.
        </p>
        {guests_line}
        {message_block}
        <p style="font-size:15px;color:#555;">Влез в профила си за да приемеш или откажеш заявката.</p>
        <div style="text-align:center;margin:30px 0;">
          <a href="{profile_url}"
             style="display:inline-block;padding:14px 32px;background:#9B1C35;color:#fff;
                    text-decoration:none;border-radius:6px;font-size:16px;font-weight:bold;">
            Виж заявката
          </a>
        </div>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(host_email, f"Нова заявка за посещение от {volunteer_name} – GoodHost 📬", body)


def send_visit_approved_email(vol_email, vol_name, host_name, from_date, to_date):
    period = f"от <strong>{from_date}</strong> до <strong>{to_date}</strong>" if from_date != to_date else f"на <strong>{from_date}</strong>"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#A8C256;padding:30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#A8C256;">Заявката ти е приета! ✅</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{vol_name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          <strong>{host_name}</strong> прие заявката ти за посещение {period}.
        </p>
        <p style="font-size:15px;color:#555;">
          След посещението не забравяй да маркираш "Посетих" в сайта за да можеш да оставиш отзив!
        </p>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(vol_email, f"Заявката ти при {host_name} е приета – GoodHost ✅", body)


def send_visit_declined_email(vol_email, vol_name, host_name, from_date, to_date, reason=''):
    period = f"от <strong>{from_date}</strong> до <strong>{to_date}</strong>" if from_date != to_date else f"на <strong>{from_date}</strong>"
    reason_block = f'<p style="font-size:14px;color:#888;font-style:italic;">Причина: {reason}</p>' if reason else ''
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
      <div style="background:#9B1C35;padding:30px;text-align:center;">
        <h1 style="color:#FBF3E4;margin:0;font-size:28px;">GoodHost</h1>
      </div>
      <div style="padding:30px;background:#fff;">
        <h2 style="color:#9B1C35;">Заявката ти беше отказана</h2>
        <p style="font-size:16px;color:#333;">Здравей, <strong>{vol_name}</strong>!</p>
        <p style="font-size:15px;color:#555;">
          За съжаление <strong>{host_name}</strong> не може да те приеме {period}.
        </p>
        {reason_block}
        <p style="font-size:15px;color:#555;">Можеш да потърсиш друг домакин в платформата.</p>
      </div>
      <div style="background:#f0f0f0;padding:15px;text-align:center;">
        <p style="font-size:13px;color:#777;margin:0;">© 2026 GoodHost. Всички права запазени.</p>
      </div>
    </div>
    """
    send_email(vol_email, f"Заявката ти при {host_name} беше отказана – GoodHost", body)


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
        help_needed      = request.form.get('help_needed', '').strip()
        offers           = request.form.get('offers', '').strip()
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
                '''INSERT INTO hosts (name, age, bio, email, phone, location, max_guests, password_hash, photos, help_needed, offers)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, int(age), about, email, phone, location, max_guests, password_hash, json.dumps(photos), help_needed or None, offers or None)
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
    visit_status_by_host = {}
    if session.get('user_type') == 'volunteer':
        rows = db.execute(
            'SELECT host_id FROM host_reviews WHERE volunteer_id = ?',
            (session['user_id'],)
        ).fetchall()
        visited_host_ids = {row['host_id'] for row in rows}
        req_rows = db.execute(
            '''SELECT host_id, status FROM visit_requests
               WHERE volunteer_id = ? AND status NOT IN ('cancelled')
               ORDER BY created_at DESC''',
            (session['user_id'],)
        ).fetchall()
        for row in req_rows:
            if row['host_id'] not in visit_status_by_host:
                visit_status_by_host[row['host_id']] = row['status']

    today = datetime.now().date()
    future_limit = today + timedelta(days=90)

    # Ръчно зададени заети дни
    busy_rows = db.execute(
        'SELECT host_id, date FROM host_busy_days WHERE date >= ? AND date <= ?',
        (str(today), str(future_limit))
    ).fetchall()
    busy_by_host = {}
    for row in busy_rows:
        busy_by_host.setdefault(row['host_id'], set()).add(str(row['date'])[:10])

    # Автоматични заети дни от одобрени заявки, запълнили капацитета
    visit_rows = db.execute(
        """SELECT vr.host_id, vr.from_date, vr.to_date, vr.num_guests, h.max_guests
           FROM visit_requests vr
           JOIN hosts h ON h.id = vr.host_id
           WHERE vr.status IN ('approved', 'completed')
           AND vr.to_date >= ? AND vr.from_date <= ?""",
        (str(today), str(future_limit))
    ).fetchall()
    from collections import defaultdict
    guest_count_by_host_day = defaultdict(lambda: defaultdict(int))
    max_guests_by_host = {}
    for row in visit_rows:
        hid = row['host_id']
        max_guests_by_host[hid] = row['max_guests']
        d = datetime.strptime(str(row['from_date'])[:10], '%Y-%m-%d').date()
        end = datetime.strptime(str(row['to_date'])[:10], '%Y-%m-%d').date()
        while d <= end and d <= future_limit:
            if d >= today:
                guest_count_by_host_day[hid][str(d)] += row['num_guests']
            d += timedelta(days=1)
    for hid, day_counts in guest_count_by_host_day.items():
        mg = max_guests_by_host.get(hid, 1)
        for day, count in day_counts.items():
            if count >= mg:
                busy_by_host.setdefault(hid, set()).add(day)

    next_available = {}
    for host in hosts_list:
        hid = host['id']
        busy = busy_by_host.get(hid, set())
        if not busy:
            next_available[hid] = None
        else:
            d = today
            while str(d) in busy and d <= future_limit:
                d += timedelta(days=1)
            next_available[hid] = None if d == today else d.strftime('%d.%m.%Y')

    db.close()
    return render_template('hosts.html', hosts=hosts_list, search=search,
                           visited_host_ids=visited_host_ids,
                           visit_status_by_host=visit_status_by_host,
                           next_available=next_available)


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

    approved_request = db.execute(
        "SELECT * FROM visit_requests WHERE volunteer_id = ? AND host_id = ? AND status = 'approved'",
        (volunteer_id, host_id)
    ).fetchone()
    if not approved_request:
        db.close()
        flash('Трябва да имаш одобрена заявка за посещение при този домакин.', 'error')
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
    db.execute(
        "UPDATE visit_requests SET status = 'completed' WHERE id = ?",
        (approved_request['id'],)
    )
    db.commit()
    db.close()

    review_link = url_for('main.review_host', token=token, _external=True)
    from_date_str = str(approved_request['from_date'])[:10]
    to_date_str   = str(approved_request['to_date'])[:10]
    send_review_invitation_email(volunteer['email'], session['user_name'], host['name'], review_link,
                                 from_date=from_date_str, to_date=to_date_str)

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


@main_bp.route('/hosts/<int:host_id>/reviews')
def host_reviews_json(host_id):
    from flask import jsonify
    db = get_db()
    rows = db.execute(
        '''SELECT r.rating, r.comment, r.created_at, v.name as volunteer_name
           FROM host_reviews r
           JOIN volunteers v ON v.id = r.volunteer_id
           WHERE r.host_id = ? AND r.token_used = 1 AND r.rating IS NOT NULL
           ORDER BY r.created_at DESC''',
        (host_id,)
    ).fetchall()
    db.close()
    result = [
        {
            'rating': row['rating'],
            'comment': row['comment'] or '',
            'volunteer_name': row['volunteer_name'],
            'created_at': str(row['created_at'])[:10],
        }
        for row in rows
    ]
    return jsonify(result)


@main_bp.route('/volunteers/<int:volunteer_id>/reviews/<int:review_id>/delete', methods=['POST'])
def delete_volunteer_review(volunteer_id, review_id):
    if 'user_id' not in session or session.get('user_type') != 'volunteer' or session['user_id'] != volunteer_id:
        flash('Нямаш право да изтриеш този коментар.', 'error')
        return redirect(url_for('main.profile'))
    db = get_db()
    db.execute(
        'DELETE FROM host_reviews WHERE id = ? AND volunteer_id = ?',
        (review_id, volunteer_id)
    )
    db.commit()
    db.close()
    flash('Коментарът беше изтрит.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/hosts/<int:host_id>/busy-days')
def get_busy_days(host_id):
    from flask import jsonify
    year  = request.args.get('year',  type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    db = get_db()

    # Ръчно зададени заети дни
    rows = db.execute(
        '''SELECT date FROM host_busy_days
           WHERE host_id = ?
             AND EXTRACT(YEAR  FROM date) = ?
             AND EXTRACT(MONTH FROM date) = ?''',
        (host_id, year, month)
    ).fetchall()
    busy_days = {str(r['date'])[:10] for r in rows}

    # Автоматични заети дни от одобрени заявки, запълнили капацитета
    host = db.execute('SELECT max_guests FROM hosts WHERE id = ?', (host_id,)).fetchone()
    if host:
        max_guests = host['max_guests']
        if month == 12:
            first_day = date_type(year, month, 1)
            last_day  = date_type(year + 1, 1, 1) - timedelta(days=1)
        else:
            first_day = date_type(year, month, 1)
            last_day  = date_type(year, month + 1, 1) - timedelta(days=1)
        visits = db.execute(
            """SELECT from_date, to_date, num_guests FROM visit_requests
               WHERE host_id = ? AND status IN ('approved', 'completed')
               AND to_date >= ? AND from_date <= ?""",
            (host_id, str(first_day), str(last_day))
        ).fetchall()
        from collections import defaultdict
        guest_count = defaultdict(int)
        for v in visits:
            d = datetime.strptime(str(v['from_date'])[:10], '%Y-%m-%d').date()
            end = datetime.strptime(str(v['to_date'])[:10], '%Y-%m-%d').date()
            while d <= end:
                if first_day <= d <= last_day:
                    guest_count[str(d)] += v['num_guests']
                d += timedelta(days=1)
        for day, count in guest_count.items():
            if count >= max_guests:
                busy_days.add(day)

    db.close()
    return jsonify({'busy_days': sorted(busy_days)})


@main_bp.route('/hosts/<int:host_id>/busy-days/toggle', methods=['POST'])
def toggle_busy_day(host_id):
    from flask import jsonify
    if 'user_id' not in session or session.get('user_type') != 'host' or session['user_id'] != host_id:
        return jsonify({'error': 'unauthorized'}), 403
    date_str = request.form.get('date', '').strip()
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'invalid date'}), 400
    db = get_db()
    existing = db.execute(
        'SELECT id FROM host_busy_days WHERE host_id = ? AND date = ?',
        (host_id, date_str)
    ).fetchone()
    if existing:
        db.execute('DELETE FROM host_busy_days WHERE host_id = ? AND date = ?', (host_id, date_str))
        db.commit()
        db.close()
        return jsonify({'status': 'removed'})
    else:
        db.execute('INSERT INTO host_busy_days (host_id, date) VALUES (?, ?)', (host_id, date_str))
        db.commit()
        db.close()
        return jsonify({'status': 'added'})


@main_bp.route('/hosts/<int:host_id>/busy-days/range', methods=['POST'])
def add_busy_range(host_id):
    from flask import jsonify
    if 'user_id' not in session or session.get('user_type') != 'host' or session['user_id'] != host_id:
        return jsonify({'error': 'unauthorized'}), 403
    data = request.get_json()
    from_str = (data or {}).get('from_date', '').strip()
    to_str   = (data or {}).get('to_date',   '').strip()
    try:
        from_date = datetime.strptime(from_str, '%Y-%m-%d').date()
        to_date   = datetime.strptime(to_str,   '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'invalid dates'}), 400
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    if (to_date - from_date).days > 365:
        return jsonify({'error': 'range too large'}), 400
    db = get_db()
    current = from_date
    added = []
    while current <= to_date:
        ds = str(current)
        if not db.execute('SELECT id FROM host_busy_days WHERE host_id=? AND date=?', (host_id, ds)).fetchone():
            db.execute('INSERT INTO host_busy_days (host_id, date) VALUES (?, ?)', (host_id, ds))
            added.append(ds)
        current += timedelta(days=1)
    db.commit()
    db.close()
    return jsonify({'status': 'ok', 'added': added})


@main_bp.route('/hosts/<int:host_id>/request-visit', methods=['POST'])
def request_visit(host_id):
    if 'user_id' not in session or session.get('user_type') != 'volunteer':
        flash('Трябва да влезеш като доброволец.', 'error')
        return redirect(url_for('main.login'))
    from_str = request.form.get('from_date', '').strip()
    to_str   = request.form.get('to_date', from_str).strip()
    message  = request.form.get('message', '').strip()
    try:
        from_date = datetime.strptime(from_str, '%Y-%m-%d')
        to_date   = datetime.strptime(to_str,   '%Y-%m-%d')
    except ValueError:
        flash('Невалидна дата.', 'error')
        return redirect(url_for('main.hosts'))
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    volunteer_id = session['user_id']
    db = get_db()
    host = db.execute('SELECT name, email, max_guests FROM hosts WHERE id = ?', (host_id,)).fetchone()
    volunteer = db.execute('SELECT name FROM volunteers WHERE id = ?', (volunteer_id,)).fetchone()
    if not host or not volunteer:
        db.close()
        flash('Домакинът не е намерен.', 'error')
        return redirect(url_for('main.hosts'))
    num_guests = max(1, min(int(request.form.get('num_guests', 1) or 1), host['max_guests']))
    # Отмени предишни pending/declined заявки за същия домакин
    db.execute(
        "UPDATE visit_requests SET status = 'cancelled' WHERE volunteer_id = ? AND host_id = ? AND status IN ('pending', 'declined')",
        (volunteer_id, host_id)
    )
    db.execute(
        'INSERT INTO visit_requests (volunteer_id, host_id, from_date, to_date, message, num_guests) VALUES (?, ?, ?, ?, ?, ?)',
        (volunteer_id, host_id, str(from_date.date()), str(to_date.date()), message or None, num_guests)
    )
    db.commit()
    db.close()
    display_from = from_date.strftime('%d.%m.%Y')
    display_to   = to_date.strftime('%d.%m.%Y')
    profile_url  = url_for('main.profile', _external=True)
    send_visit_request_email(host['email'], host['name'], volunteer['name'],
                              display_from, display_to, message, profile_url, num_guests=num_guests)
    flash(f'Заявката е изпратена до {host["name"]}! Ще получиш имейл при одобрение.', 'success')
    return redirect(url_for('main.hosts'))


@main_bp.route('/visits/<int:visit_id>/approve', methods=['POST'])
def approve_visit(visit_id):
    if 'user_id' not in session or session.get('user_type') != 'host':
        flash('Нямаш право за това действие.', 'error')
        return redirect(url_for('main.login'))
    host_id = session['user_id']
    db = get_db()
    visit = db.execute(
        'SELECT * FROM visit_requests WHERE id = ? AND host_id = ?',
        (visit_id, host_id)
    ).fetchone()
    if not visit or visit['status'] != 'pending':
        db.close()
        flash('Заявката не е намерена.', 'error')
        return redirect(url_for('main.profile'))
    db.execute("UPDATE visit_requests SET status = 'approved' WHERE id = ?", (visit_id,))
    db.commit()
    volunteer = db.execute('SELECT name, email FROM volunteers WHERE id = ?', (visit['volunteer_id'],)).fetchone()
    host = db.execute('SELECT name FROM hosts WHERE id = ?', (host_id,)).fetchone()
    db.close()
    send_visit_approved_email(
        volunteer['email'], volunteer['name'], host['name'],
        str(visit['from_date'])[:10], str(visit['to_date'])[:10]
    )
    flash(f'Прие си заявката на {volunteer["name"]}.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/visits/<int:visit_id>/decline', methods=['POST'])
def decline_visit(visit_id):
    if 'user_id' not in session or session.get('user_type') != 'host':
        flash('Нямаш право за това действие.', 'error')
        return redirect(url_for('main.login'))
    host_id = session['user_id']
    reason  = request.form.get('reason', '').strip()
    db = get_db()
    visit = db.execute(
        'SELECT * FROM visit_requests WHERE id = ? AND host_id = ?',
        (visit_id, host_id)
    ).fetchone()
    if not visit or visit['status'] != 'pending':
        db.close()
        flash('Заявката не е намерена.', 'error')
        return redirect(url_for('main.profile'))
    db.execute(
        "UPDATE visit_requests SET status = 'declined', decline_reason = ? WHERE id = ?",
        (reason or None, visit_id)
    )
    db.commit()
    volunteer = db.execute('SELECT name, email FROM volunteers WHERE id = ?', (visit['volunteer_id'],)).fetchone()
    host = db.execute('SELECT name FROM hosts WHERE id = ?', (host_id,)).fetchone()
    db.close()
    send_visit_declined_email(
        volunteer['email'], volunteer['name'], host['name'],
        str(visit['from_date'])[:10], str(visit['to_date'])[:10], reason
    )
    flash(f'Отказа заявката на {volunteer["name"]}.', 'success')
    return redirect(url_for('main.profile'))


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


@main_bp.route('/hosts/<int:host_id>/update-bio', methods=['POST'])
def update_bio(host_id):
    if 'user_id' not in session or session.get('user_type') != 'host' or session['user_id'] != host_id:
        return redirect(url_for('main.profile'))

    bio = request.form.get('bio', '').strip()
    db = get_db()
    db.execute('UPDATE hosts SET bio = ? WHERE id = ?', (bio, host_id))
    db.commit()
    db.close()
    flash('Описанието беше обновено успешно.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/hosts/<int:host_id>/update-help-needed', methods=['POST'])
def update_help_needed(host_id):
    if 'user_id' not in session or session.get('user_type') != 'host' or session['user_id'] != host_id:
        return redirect(url_for('main.profile'))

    help_needed = request.form.get('help_needed', '').strip()
    db = get_db()
    db.execute('UPDATE hosts SET help_needed = ? WHERE id = ?', (help_needed or None, host_id))
    db.commit()
    db.close()
    flash('Полето "Търся помощ с" беше обновено успешно.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/hosts/<int:host_id>/update-offers', methods=['POST'])
def update_offers(host_id):
    if 'user_id' not in session or session.get('user_type') != 'host' or session['user_id'] != host_id:
        return redirect(url_for('main.profile'))

    offers = request.form.get('offers', '').strip()
    db = get_db()
    db.execute('UPDATE hosts SET offers = ? WHERE id = ?', (offers or None, host_id))
    db.commit()
    db.close()
    flash('Полето "Предлагам" беше обновено успешно.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/volunteers/<int:volunteer_id>/delete', methods=['POST'])
def delete_volunteer(volunteer_id):
    if 'user_id' not in session or session.get('user_type') != 'volunteer':
        return redirect(url_for('main.login'))
    if session['user_id'] != volunteer_id:
        return redirect(url_for('main.profile'))
    db = get_db()
    db.execute('DELETE FROM volunteers WHERE id = ?', (volunteer_id,))
    db.commit()
    db.close()
    session.clear()
    flash('Профилът ти беше изтрит успешно.', 'success')
    return redirect(url_for('main.index'))


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
    pending_visit_requests = []
    volunteer_reviews = []
    if current_user_type == 'host':
        user = db.execute('SELECT * FROM hosts WHERE id = ?', (current_user_id,)).fetchone()
        rows = db.execute(
            '''SELECT vr.*, v.name as volunteer_name, v.email as volunteer_email
               FROM visit_requests vr
               JOIN volunteers v ON v.id = vr.volunteer_id
               WHERE vr.host_id = ? AND vr.status = 'pending'
               ORDER BY vr.created_at DESC''',
            (current_user_id,)
        ).fetchall()
        pending_visit_requests = [
            {**dict(row),
             'from_date': str(row['from_date'])[:10],
             'to_date': str(row['to_date'])[:10],
             'created_at': str(row['created_at'])[:10]}
            for row in rows
        ]
    else:
        user = db.execute('SELECT * FROM volunteers WHERE id = ?', (current_user_id,)).fetchone()
        rows = db.execute(
            '''SELECT r.id, r.rating, r.comment, r.created_at, h.name as host_name
               FROM host_reviews r
               JOIN hosts h ON h.id = r.host_id
               WHERE r.volunteer_id = ? AND r.token_used = 1 AND r.rating IS NOT NULL
               ORDER BY r.created_at DESC''',
            (current_user_id,)
        ).fetchall()
        volunteer_reviews = [
            {**dict(row), 'created_at': str(row['created_at'])[:10]}
            for row in rows
        ]
    db.close()

    is_verified = bool(user['id_verified']) if user and 'id_verified' in user.keys() else False
    verification_url = url_for('verify.verify_page', user_type=current_user_type, user_id=current_user_id)

    return render_template(
        'profile.html',
        user=user,
        is_verified=is_verified,
        verification_url=verification_url,
        stripe_publishable_key=config.STRIPE_PUBLISHABLE_KEY,
        volunteer_reviews=volunteer_reviews,
        pending_visit_requests=pending_visit_requests
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


CHATBOT_SYSTEM_PROMPT = """Ти си GoodHost Асистент — помощен AI чатбот на платформата GoodHost.

GoodHost е българска платформа за доброволен туризъм, която свързва доброволци и домакини из цяла България. Доброволците получават безплатен престой, като помагат с ежедневни задачи на домакините.

Можеш да помагаш с въпроси като:
- Как работи платформата
- Как да се регистрираш като доброволец или домакин
- Какви са правилата и очакванията
- Как да намериш домакин или доброволец
- Как да се свържеш с домакин
- Въпроси за профила, верификацията и безопасността

Отговаряй на български език, кратко и ясно. Ако не знаеш отговора, кажи на потребителя да се свърже с нас на goodhost230@gmail.com."""


@main_bp.route('/api/chat', methods=['POST'])
def chat():
    if not config.GROQ_API_KEY:
        return jsonify({'error': 'Чатботът не е конфигуриран.'}), 503

    data = request.get_json(silent=True)
    if not data or 'messages' not in data:
        return jsonify({'error': 'Невалидна заявка.'}), 400

    messages = data['messages']
    if not isinstance(messages, list) or len(messages) == 0:
        return jsonify({'error': 'Невалидни съобщения.'}), 400

    # Keep only last 10 messages to limit tokens
    messages = messages[-10:]
    for msg in messages:
        if msg.get('role') not in ('user', 'assistant') or not isinstance(msg.get('content'), str):
            return jsonify({'error': 'Невалиден формат на съобщенията.'}), 400

    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            max_tokens=500,
            messages=[{'role': 'system', 'content': CHATBOT_SYSTEM_PROMPT}] + messages,
        )
        return jsonify({'reply': response.choices[0].message.content})
    except Exception as e:
        print(f'[Chatbot грешка] {e}')
        return jsonify({'error': 'Грешка при свързване с AI.'}), 500
