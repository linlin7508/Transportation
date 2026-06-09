from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.arena import Arena
from app.services.fight_service import change_master

bp = Blueprint("arena_v2", __name__, url_prefix="/api/arena")

@bp.route("", methods=["GET"])
def get_arenas():
    arenas = Arena.query.all()
    return jsonify([a.to_dict() for a in arenas])

@bp.route("/<int:arena_id>", methods=["GET"])
def get_arena(arena_id):
    arena = Arena.query.get_or_404(arena_id)
    return jsonify(arena.to_dict())

@bp.route("/<int:arena_id>/claim", methods=["POST"])
def claim_arena(arena_id):
    """直接佔領無人的道館"""
    from flask import g
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
        
    data = request.json
    creature_id = data.get("creature_id")
    
    if not creature_id:
        return jsonify({"error": "Missing creature_id"}), 400
        
    arena = Arena.query.get_or_404(arena_id)
    if arena.master_id is not None:
        return jsonify({"error": "Arena already occupied. Use challenge endpoint instead."}), 400
        
    change_master(arena, user.id, creature_id)
    return jsonify({"success": True, "message": "Arena claimed", "arena": arena.to_dict()})
