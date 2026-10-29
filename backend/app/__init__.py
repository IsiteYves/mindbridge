from flask import Flask

from app.api import api_bp
from app.api.errors import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    register_error_handlers(app)
    return app
