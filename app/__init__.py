
from flask import Flask
from app.database import init_db

def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = "expense-tracker-secret-key"

    # Initialize database
    init_db(app)

    # Register website routes
    from app.routes import main
    app.register_blueprint(main)

    return app
