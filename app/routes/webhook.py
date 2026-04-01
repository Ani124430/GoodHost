from flask import Blueprint, request, jsonify
from app.verification import handle_webhook

webhook_bp = Blueprint('webhook', __name__)


@webhook_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')

    success = handle_webhook(payload, sig_header)

    if not success:
        return jsonify({'error': 'Invalid signature'}), 400

    return jsonify({'status': 'ok'}), 200
