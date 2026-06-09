from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.arena import Battle
from app.services.fight_service import process_fight

bp = Blueprint("fight_v2", __name__, url_prefix="/api/fight")

@bp.route("/start", methods=["POST"])
def start_fight():
    from flask import g
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
        
    data = request.json
    attacker_creature_id = data.get("attacker_creature_id")
    arena_id = data.get("arena_id")
    
    if not all([attacker_creature_id, arena_id]):
        return jsonify({"error": "Missing parameters"}), 400
        
    try:
        result = process_fight(
            arena_id=arena_id,
            attacker_user_id=user.id,
            attacker_creature_id=attacker_creature_id
        )
        return jsonify({"success": True, "result": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.route("/history/me", methods=["GET"])
def fight_history():
    from flask import g
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
        
    # 用戶為挑戰者或守衛者的戰鬥
    battles = Battle.query.filter(
        (Battle.challenger_id == user.id) | (Battle.defender_id == user.id)
    ).order_by(Battle.created_at.desc()).all()
    
    return jsonify([b.to_dict() for b in battles])
