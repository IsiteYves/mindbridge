from flask import Blueprint

from app.api.assignments import assignments_bp
from app.api.auth import auth_bp
from app.api.canvas import canvas_bp
from app.api.health import health_bp
from app.api.milestones import milestones_bp
from app.api.wellness import wellness_bp

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
api_bp.register_blueprint(health_bp)
api_bp.register_blueprint(auth_bp)
api_bp.register_blueprint(assignments_bp)
api_bp.register_blueprint(milestones_bp)
api_bp.register_blueprint(wellness_bp)
api_bp.register_blueprint(canvas_bp)
