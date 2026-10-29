from flask import Blueprint

from app.api.health import health_bp

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
api_bp.register_blueprint(health_bp)
