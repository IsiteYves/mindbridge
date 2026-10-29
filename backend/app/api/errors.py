from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        response = jsonify(error=error.name, message=error.description)
        response.status_code = error.code
        return response
