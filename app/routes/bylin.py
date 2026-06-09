from datetime import datetime

from flask import Blueprint, g, jsonify, render_template, request, session

from app.extensions import db
from app.models.profile import Profile

bylin_bp = Blueprint("bylin", __name__, url_prefix="/bylin")


def _firebase_config():
    return {
        "apiKey": "",
        "authDomain": "",
        "projectId": "",
        "storageBucket": "",
        "messagingSenderId": "",
        "appId": "",
    }


def _ensure_session_user():
    if "user" not in session:
        session["user"] = {"uid": session.get("user_id", ""), "username": "訪客訓練師"}


@bylin_bp.get("/myelf", endpoint="myelf")
def myelf():
    _ensure_session_user()
    return render_template("bylin/myelf.html", firebase_config=_firebase_config())


@bylin_bp.get("/backpack", endpoint="backpack")
def backpack():
    _ensure_session_user()
    return render_template("bylin/mybag.html")


@bylin_bp.get("/myarena", endpoint="myarena")
def myarena():
    _ensure_session_user()
    return render_template("bylin/myarena.html")


@bylin_bp.get("/magic-circle-details", endpoint="magic_circle_details")
def magic_circle_details():
    _ensure_session_user()
    return render_template("bylin/magic_circle_details.html")


@bylin_bp.get("/potion-details", endpoint="potion_details")
def potion_details():
    _ensure_session_user()
    return render_template("bylin/potion_details.html")


@bylin_bp.get("/api/backpack")
def api_backpack():
    return jsonify({"success": True, "items": [], "inventory": {}})


@bylin_bp.get("/api/myarena")
def api_myarena():
    from app.routes.game import _load_cached_arenas, _normalize_arena_payload

    user = getattr(g, "user", None)
    user_id = str(user.id) if user else str(session.get("user_id") or session.get("user", {}).get("uid") or "")
    arenas = []
    if not user_id:
        return jsonify({
            "success": True,
            "arenas": [],
            "base_gyms": [],
            "total_arenas": 0,
            "total_base_gyms": 0,
        })

    for arena in _load_cached_arenas().values():
        owner_id = arena.get("ownerPlayerId") if isinstance(arena, dict) else None
        if not owner_id or str(owner_id) != user_id:
            continue

        normalized = _normalize_arena_payload(arena)
        normalized["position"] = normalized.get("position_object") or {
            "lat": (normalized.get("position") or [None, None])[0],
            "lng": (normalized.get("position") or [None, None])[1],
        }
        normalized["user_arena_data"] = {
            "occupied_at": datetime.fromtimestamp((arena.get("updatedAt") or 0) / 1000).isoformat()
            if arena.get("updatedAt")
            else None
        }
        normalized["hours_occupied"] = len(normalized.get("rewards", {}).get("available_rewards", []))
        arenas.append(normalized)

    return jsonify({
        "success": True,
        "arenas": arenas,
        "base_gyms": [],
        "total_arenas": len(arenas),
        "total_base_gyms": 0,
    })


@bylin_bp.post("/api/collect-arena-rewards")
def collect_arena_rewards():
    from app.routes.game import _arena_available_rewards, _find_cached_arena_key, _load_cached_arenas, _write_cached_arenas

    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "請先登入再領取獎勵"}), 401

    payload = request.get_json(silent=True) or {}
    arena_id = str(payload.get("arena_id") or "").strip()
    arena_key = _find_cached_arena_key(arena_id)
    if not arena_key:
        return jsonify({"success": False, "message": "找不到指定道館"}), 404

    arenas = _load_cached_arenas()
    arena = arenas.get(arena_key)
    if not isinstance(arena, dict):
        return jsonify({"success": False, "message": "道館資料格式錯誤"}), 500
    if arena.get("ownerPlayerId") != user.id:
        return jsonify({"success": False, "message": "只有目前擂主可以領取獎勵"}), 403

    collected_items = _arena_available_rewards(arena)
    if not collected_items:
        return jsonify({"success": False, "message": "目前沒有可領取的獎勵"}), 400

    profile = Profile.query.filter_by(user_id=user.id).first()
    experience = sum(int(item.get("quantity") or 0) for item in collected_items if item.get("type") == "experience")
    if profile and experience:
        profile.exp = (profile.exp or 0) + experience
        profile.level = max(profile.level or 1, (profile.exp // 100) + 1)

    arena["rewards"] = {"available_rewards": [], "claimed": True}
    arenas[arena_key] = arena
    _write_cached_arenas(arenas)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "成功領取道館獎勵",
        "collected_items": collected_items,
    })


@bylin_bp.get("/api/magic-circle-data")
def api_magic_circle_data():
    return jsonify({
        "success": True,
        "magic_circles": [
            {"key": "normal", "count": 3},
            {"key": "advanced", "count": 1},
            {"key": "premium", "count": 0},
        ],
    })


@bylin_bp.get("/api/potion-data")
def api_potion_data():
    return jsonify({
        "success": True,
        "potions": [
            {"key": "normal", "count": 5},
            {"key": "advanced", "count": 2},
            {"key": "high", "count": 0},
        ],
    })
