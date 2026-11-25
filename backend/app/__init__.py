from flask import Flask
from flask_cors import CORS

from app.api import api_bp
from app.api.errors import register_error_handlers
from app.config import Config
from app import models  # noqa: F401  registers tables with SQLAlchemy metadata
from app.extensions import db, migrate
MIN_SECRET_KEY_LENGTH = 32


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY must be set")
    if len(app.config["SECRET_KEY"]) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters")

    db.init_app(app)
    migrate.init_app(app, db)

    # Only the /api/ routes accept cross-origin requests, and only from the configured origins.
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)
    app.register_blueprint(api_bp)
    register_error_handlers(app)

    from app.cli import register as register_cli
    register_cli(app)

    return app