import os
from flask import Flask
from app.database import init_db

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "development-key-change-this"
    )

    init_db(app)

    from app.routes import main
    app.register_blueprint(main)

    return app