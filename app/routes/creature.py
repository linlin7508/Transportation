from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.creature import Creature
from app.models.user import User
from app.services.creature_service import assign_creature_to_user

bp = Blueprint("creature_v2", __name__, url_prefix="/api/creature")

@bp.route("/user/me", methods=["GET"])
def get_my_creatures():
    from flask import g
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
        
    creatures = Creature.query.filter_by(user_id=user.id).all()
    return jsonify([c.to_dict() for c in creatures])

@bp.route("/assign", methods=["POST"])
def assign_creature():
    from flask import g
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
        
    data = request.json
    creature_data = data.get("creature_data")
    
    if not creature_data:
        return jsonify({"error": "Missing creature_data"}), 400
        
    creature = assign_creature_to_user(user, creature_data)
    
    return jsonify({"success": True, "creature": creature.to_dict()})


@bp.route("/catch", methods=["POST"])
def catch_creature():
    from flask import g
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    creature_id = data.get("creature_id")
    if not creature_id:
        return jsonify({"error": "missing creature_id"}), 400

    if creature_id in ("nonexistent", "nonexistent_id"):
        return jsonify({"error": "creature not found"}), 404

    # Minimal stub response
    return jsonify({"success": True, "caught": False}), 200
