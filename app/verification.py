import stripe
import os
from dotenv import load_dotenv
from app.database import get_db

load_dotenv()


def create_verification_session(user_type, user_id):
    """
    Създава Stripe VerificationSession и записва ID-то в БД.
    user_type: 'host' или 'volunteer'
    Връща client_secret за фронтенда.
    """
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
    session = stripe.identity.VerificationSession.create(
        type='document',
        metadata={
            'user_type': user_type,
            'user_id': str(user_id),
        },
        options={
            'document': {
                'require_live_capture': True,
                'require_matching_selfie': True,
            }
        },
    )

    table = 'hosts' if user_type == 'host' else 'volunteers'
    conn = get_db()
    conn.execute(
        f'UPDATE {table} SET stripe_verification_id = ? WHERE id = ?',
        (session.id, user_id)
    )
    conn.commit()
    conn.close()

    return session.client_secret


def handle_webhook(payload, sig_header):
    """
    Обработва Stripe webhook събитие.
    При успешна верификация update-ва id_verified = 1 в БД.
    """
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        return False

    if event['type'] == 'identity.verification_session.verified':
        vs = event['data']['object']
        user_type = vs['metadata'].get('user_type')
        user_id = vs['metadata'].get('user_id')

        if user_type and user_id:
            table = 'hosts' if user_type == 'host' else 'volunteers'
            conn = get_db()
            conn.execute(
                f'UPDATE {table} SET id_verified = 1 WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()

    elif event['type'] == 'identity.verification_session.requires_input':
        vs = event['data']['object']
        user_type = vs['metadata'].get('user_type')
        user_id = vs['metadata'].get('user_id')

        if user_type and user_id:
            table = 'hosts' if user_type == 'host' else 'volunteers'
            conn = get_db()
            conn.execute(
                f'UPDATE {table} SET id_verified = 0 WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()

    return True


def get_verification_status(user_type, user_id):
    """
    Връща текущия статус на верификацията от Stripe.
    Статуси: requires_input, processing, verified, canceled
    """
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
    table = 'hosts' if user_type == 'host' else 'volunteers'
    conn = get_db()
    row = conn.execute(
        f'SELECT stripe_verification_id, id_verified FROM {table} WHERE id = ?',
        (user_id,)
    ).fetchone()
    conn.close()

    if not row or not row['stripe_verification_id']:
        return {'verified': False, 'status': 'not_started'}

    if row['id_verified']:
        return {'verified': True, 'status': 'verified'}

    session = stripe.identity.VerificationSession.retrieve(
        row['stripe_verification_id']
    )

    if session.status == 'verified':
        if not row['id_verified']:
            conn = get_db()
            conn.execute(
                f'UPDATE {table} SET id_verified = 1 WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()
        return {'verified': True, 'status': 'verified'}

    return {'verified': False, 'status': session.status}
