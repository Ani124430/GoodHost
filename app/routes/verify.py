from flask import Blueprint, jsonify, request, render_template
from app.verification import create_verification_session, get_verification_status
from app.database import get_db
import config

verify_bp = Blueprint('verify', __name__)


@verify_bp.route('/verify')
def verify_page():
    user_type = request.args.get('user_type', 'host')
    user_id = request.args.get('user_id', '')
    return render_template(
        'verify.html',
        stripe_publishable_key=config.STRIPE_PUBLISHABLE_KEY,
        user_type=user_type,
        user_id=user_id,
    )


@verify_bp.route('/verify/start', methods=['POST'])
def start_verification():
    """
    Фронтендът извиква това след регистрация.
    Изпраща: { "user_type": "host" или "volunteer", "user_id": 1 }
    Връща:   { "client_secret": "vsess_..." }
    """
    data = request.get_json()
    user_type = data.get('user_type')
    user_id = data.get('user_id')

    if user_type not in ('host', 'volunteer') or not user_id:
        return jsonify({'error': 'Невалидни данни'}), 400

    table = 'hosts' if user_type == 'host' else 'volunteers'
    conn = get_db()
    user = conn.execute(
        f'SELECT id FROM {table} WHERE id = ?', (user_id,)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Потребителят не е намерен'}), 404

    client_secret = create_verification_session(user_type, user_id)
    return jsonify({'client_secret': client_secret}), 200


@verify_bp.route('/verify/status', methods=['GET'])
def check_status():
    """
    Проверява статуса на верификацията.
    Параметри: ?user_type=host&user_id=1
    Връща: { "verified": true/false, "status": "verified/processing/..." }
    """
    user_type = request.args.get('user_type')
    user_id = request.args.get('user_id')

    if user_type not in ('host', 'volunteer') or not user_id:
        return jsonify({'error': 'Невалидни данни'}), 400

    status = get_verification_status(user_type, int(user_id))
    return jsonify(status), 200
