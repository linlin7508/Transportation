from flask import Blueprint, request, jsonify, session
from app.services.auth_service import register, login

auth_bp = Blueprint("auth_v2", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register_route():
    data = request.json
    
    if not all(k in data for k in ("email", "password", "username")):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        user = register(
            data["email"],
            data["password"],
            data["username"]
        )
        return jsonify({"id": str(user.id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    
    if not all(k in data for k in ("email", "password")):
        return jsonify({"error": "Missing email or password"}), 400

    user = login(data["email"], data["password"])
    if not user:
        return jsonify({"error": "invalid credentials"}), 401

    session["user_id"] = str(user.id)
    return jsonify({"message": "login success"})

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return jsonify({"message": "logged out"})
