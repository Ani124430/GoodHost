from flask import Flask
from config import SECRET_KEY
from app.database import init_db


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = SECRET_KEY

    init_db()

    from app.routes.main import main_bp
    from app.routes.webhook import webhook_bp
    from app.routes.verify import verify_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(verify_bp)

    return app
