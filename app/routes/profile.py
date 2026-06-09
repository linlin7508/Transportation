from flask import Blueprint, g, jsonify
from app.models.profile import Profile

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.get("/me")
def me():
    if not getattr(g, "user", None):
        return jsonify({"error": "unauthorized"}), 401

    profile = Profile.query.filter_by(user_id=g.user.id).first()

    if not profile:
        return jsonify({"error": "profile not found"}), 404

    resp = {
        "user_id": str(g.user.id),
        "username": g.user.username,
        "profile": {
            "level": profile.level,
            "exp": profile.exp,
            "coins": profile.coins,
            "win": profile.win_count,
            "lose": profile.lose_count,
            "catch": profile.catch_count
        }
    }

    # Backwards-compatible top-level fields for tests/tools that expect them
    resp["level"] = profile.level
    resp["exp"] = profile.exp
    resp["coins"] = profile.coins

    return jsonify(resp)

