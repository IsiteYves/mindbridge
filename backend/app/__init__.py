from flask import Flask

from app.api import api_bp
from app.api.errors import register_error_handlers
from app.config import Config
from app.extensions import db, migrate


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(api_bp)
    register_error_handlers(app)
    return app
