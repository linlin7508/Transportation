from flask import Blueprint, g, jsonify
from app.extensions import db
from app.services.user_stats import get_user_stats

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.get("/me")
def me():
    if not getattr(g, "user", None):
        return jsonify({"error": "unauthorized"}), 401

    stats = get_user_stats(g.user.id)
    db.session.commit()

    resp = {
        "user_id": str(g.user.id),
        "username": g.user.username,
        "profile": {
            "level": stats["level"],
            "exp": stats["exp"],
            "exp_current": stats["exp_current"],
            "exp_next": stats["exp_next"],
            "exp_progress_percent": stats["exp_progress_percent"],
            "coins": stats["coins"],
            "win": stats["win_count"],
            "lose": stats["lose_count"],
            "catch": stats["captured_count"],
            "arena": stats["arena_count"],
            "battle": stats["battle_count"],
        },
        "stats": stats,
    }

    # Backwards-compatible top-level fields for tests/tools that expect them
    resp["level"] = stats["level"]
    resp["exp"] = stats["exp"]
    resp["coins"] = stats["coins"]

    return jsonify(resp)
