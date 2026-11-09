
import os
from flask import Flask
from flask_login import LoginManager
from app.database import db, init_db, User
from dotenv import load_dotenv

load_dotenv()

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is missing!")

    init_db(app)

    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    from app.routes import main
    app.register_blueprint(main)

    return app


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None
