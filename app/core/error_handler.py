from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle(e):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "message": str(e),
                "code": 500
            }
        }), 500
