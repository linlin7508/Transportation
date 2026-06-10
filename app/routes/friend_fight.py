import random
import string
import time
import uuid
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

from flask import Blueprint, g, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.models.creature import Creature
from app.models.friend_fight_room import FriendFightRoom
from app.models.fight import calculate_battle
from app.services.creature_images import get_creature_image_url


friend_fight_bp = Blueprint("friend_fight", __name__, url_prefix="/friend-fight")
_PASSERBY_WAITING: dict[str, dict] = {}
_PASSERBY_RESULTS: dict[str, dict] = {}
_PASSERBY_WAIT_SECONDS = 5
_PASSERBY_MATCH_MAX_AGE = 30
_CREATURE_CSV = Path(__file__).resolve().parents[1] / "data" / "creatures" / "current_creatures.csv"
_CPU_NAMES = ["山腳路人", "指南山旅人", "公車站訓練師", "達賢夜讀生", "四維堂守望者"]


def _current_user():
    return getattr(g, "user", None)


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance_meters(lat1, lng1, lat2, lng2) -> float:
    radius = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * radius * asin(sqrt(a))


def _cleanup_passerby_pool(now: float | None = None) -> None:
    current = now or time.time()
    expired_tokens = [
        token for token, entry in _PASSERBY_WAITING.items()
        if current - float(entry.get("created_at", 0)) > _PASSERBY_MATCH_MAX_AGE
    ]
    for token in expired_tokens:
        _PASSERBY_WAITING.pop(token, None)


def _battle_for_player(player_creature: dict, opponent_creature: dict, opponent_name: str, source: str) -> dict:
    raw_result = calculate_battle(player_creature, opponent_creature)
    winner = raw_result.get("winner")
    if winner == "host":
        winner = "player"
    elif winner == "visitor":
        winner = "opponent"

    return {
        "winner": winner,
        "winner_name": raw_result.get("winner_name"),
        "loser_name": raw_result.get("loser_name"),
        "battle_details": raw_result.get("battle_details", {}),
        "player_creature": player_creature,
        "opponent_creature": opponent_creature,
        "opponent_name": opponent_name,
        "opponent_source": source,
    }


def _mirror_passerby_result(result: dict, player_name: str) -> dict:
    winner = result.get("winner")
    if winner == "player":
        winner = "opponent"
    elif winner == "opponent":
        winner = "player"

    return {
        **result,
        "winner": winner,
        "player_creature": result.get("opponent_creature"),
        "opponent_creature": result.get("player_creature"),
        "opponent_name": player_name,
        "opponent_source": "nearby_player",
    }


def _random_cpu_creature() -> dict:
    try:
        import csv
        with _CREATURE_CSV.open(encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
    except (FileNotFoundError, OSError):
        rows = []

    if rows:
        row = random.choice(rows)
        name = row.get("C_Name") or row.get("name") or "野生精靈"
        try:
            hp_min = int(row.get("HP_Min") or 600)
            hp_max = int(row.get("HP_Max") or 1800)
            atk_min = int(row.get("ATK_Min") or 100)
            atk_max = int(row.get("ATK_Max") or 350)
        except (TypeError, ValueError):
            hp_min, hp_max, atk_min, atk_max = 600, 1800, 100, 350
        attack = random.randint(min(atk_min, atk_max), max(atk_min, atk_max))
        return {
            "id": f"cpu-{uuid.uuid4().hex[:8]}",
            "name": name,
            "species": row.get("Rate") or "R",
            "rarity": row.get("Rate") or "R",
            "rate": row.get("Rate") or "R",
            "element_type": row.get("Type") or "normal",
            "element": row.get("Type") or "normal",
            "type": row.get("Type") or "normal",
            "attack": attack,
            "power": attack,
            "hp": random.randint(min(hp_min, hp_max), max(hp_min, hp_max)),
            "image_url": get_creature_image_url(name),
        }

    return {
        "id": f"cpu-{uuid.uuid4().hex[:8]}",
        "name": "虛弱兔",
        "species": "N",
        "rarity": "N",
        "rate": "N",
        "element_type": "normal",
        "element": "normal",
        "type": "normal",
        "attack": random.randint(80, 160),
        "power": random.randint(80, 160),
        "hp": random.randint(500, 1000),
        "image_url": get_creature_image_url("虛弱兔"),
    }


def _room_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(30):
        room_id = "".join(random.choice(alphabet) for _ in range(8))
        if not FriendFightRoom.query.filter_by(room_id=room_id).first():
            return room_id
    raise RuntimeError("unable to generate unique room id")


def _creature_for_user(creature_id, user_id: str) -> Creature | None:
    try:
        creature_id = int(creature_id)
    except (TypeError, ValueError):
        return None

    creature = db.session.get(Creature, creature_id)
    if not creature or creature.user_id != user_id:
        return None
    return creature


def _room_payload(room: FriendFightRoom) -> dict:
    return {
        "room_id": room.room_id,
        "status": room.status,
        "host_user_id": room.host_user_id,
        "visitor_user_id": room.visitor_user_id,
        "host_creature": room.host_creature_data,
        "visitor_creature": room.visitor_creature_data,
        "battle_result": room.battle_result,
    }


def _get_room(room_id: str | None) -> FriendFightRoom | None:
    normalized = (room_id or "").strip().upper()
    if not normalized:
        return None
    return FriendFightRoom.query.filter_by(room_id=normalized).first()


@friend_fight_bp.get("/", endpoint="index")
def index():
    return redirect(url_for("friend_fight.choose_fight"))


@friend_fight_bp.get("/choose", endpoint="choose_fight")
def choose_fight():
    return render_template("friend_fight/choose_fight.html")


@friend_fight_bp.get("/host", endpoint="host_fight")
def host_fight():
    return render_template("friend_fight/host_fight.html")


@friend_fight_bp.get("/join", endpoint="join_fight")
def join_fight():
    return render_template("friend_fight/join_fight.html")


@friend_fight_bp.get("/passerby", endpoint="passerby_fight")
def passerby_fight():
    return render_template("friend_fight/passerby_fight.html")


@friend_fight_bp.post("/create-room", endpoint="create_room")
def create_room():
    user = _current_user()
    if not user:
        return jsonify({"success": False, "message": "請先登入再創建房間"}), 401

    data = request.get_json(silent=True) or {}
    creature = _creature_for_user(data.get("creature_id"), user.id)
    if not creature:
        return jsonify({"success": False, "message": "找不到你的出戰精靈"}), 400

    room = FriendFightRoom(
        room_id=_room_code(),
        status="waiting",
        host_user_id=user.id,
        host_creature_id=creature.id,
        host_creature_data=creature.to_dict(),
    )
    db.session.add(room)
    db.session.commit()
    return jsonify({"success": True, "room_id": room.room_id, "room_data": _room_payload(room)})


@friend_fight_bp.get("/room/<room_id>/status", endpoint="room_status")
def room_status(room_id):
    room = _get_room(room_id)
    if not room:
        return jsonify({"success": False, "message": "房間不存在或已過期"}), 404
    return jsonify({"success": True, "room_id": room.room_id, "room_data": _room_payload(room)})


@friend_fight_bp.post("/start-battle", endpoint="start_battle")
def start_battle():
    user = _current_user()
    if not user:
        return jsonify({"success": False, "message": "請先登入再開始戰鬥"}), 401

    data = request.get_json(silent=True) or {}
    room = _get_room(data.get("room_id"))
    if not room:
        return jsonify({"success": False, "message": "房間不存在或已過期"}), 404
    if room.host_user_id != user.id:
        return jsonify({"success": False, "message": "只有房主可以開始戰鬥"}), 403
    if room.status != "ready" or not room.visitor_creature_data:
        return jsonify({"success": False, "message": "等待對手加入後才能開始戰鬥"}), 400

    room.status = "finished"
    room.battle_result = calculate_battle(room.host_creature_data, room.visitor_creature_data)
    db.session.commit()
    return jsonify({"success": True, "room_data": _room_payload(room)})


@friend_fight_bp.post("/room/<room_id>/delete", endpoint="delete_room")
def delete_room(room_id):
    user = _current_user()
    room = _get_room(room_id)
    if not room:
        return jsonify({"success": True, "room_id": (room_id or "").upper()})
    if not user:
        return jsonify({"success": False, "message": "請先登入再清理房間"}), 401
    if room.host_user_id != user.id:
        return jsonify({"success": False, "message": "只有房主可以清理房間"}), 403

    db.session.delete(room)
    db.session.commit()
    return jsonify({"success": True, "room_id": room.room_id})


@friend_fight_bp.get("/visitor/<room_id>", endpoint="visitor_fight")
def visitor_fight(room_id):
    user = _current_user()
    room = _get_room(room_id)
    user_role = "visitor"
    if room and user and room.host_user_id == user.id:
        user_role = "host"
    return render_template("friend_fight/visitor_fight.html", room_id=(room_id or "").upper(), user_role=user_role)


@friend_fight_bp.post("/join-room", endpoint="join_room")
def join_room():
    data = request.get_json(silent=True) or {}
    room = _get_room(data.get("room_id"))
    if not room:
        return jsonify({"success": False, "message": "找不到房間，請確認房間ID是否正確"}), 404
    if room.status not in ("waiting", "ready"):
        return jsonify({"success": False, "message": "房間已結束或不可加入"}), 400
    if room.visitor_user_id:
        return jsonify({"success": False, "message": "房間已滿"}), 400

    user = _current_user()
    if user and room.host_user_id == user.id:
        return jsonify({"success": False, "message": "不能加入自己創建的房間"}), 400

    return jsonify({"success": True, "room_data": _room_payload(room)})


@friend_fight_bp.post("/confirm-join", endpoint="confirm_join")
def confirm_join():
    user = _current_user()
    if not user:
        return jsonify({"success": False, "message": "請先登入再加入房間"}), 401

    data = request.get_json(silent=True) or {}
    room = _get_room(data.get("room_id"))
    if not room:
        return jsonify({"success": False, "message": "房間不存在或已過期"}), 404
    if room.status != "waiting":
        return jsonify({"success": False, "message": "房間已滿或不可加入"}), 400
    if room.host_user_id == user.id:
        return jsonify({"success": False, "message": "不能加入自己創建的房間"}), 400

    creature = _creature_for_user(data.get("creature_id"), user.id)
    if not creature:
        return jsonify({"success": False, "message": "找不到你的出戰精靈"}), 400

    room.status = "ready"
    room.visitor_user_id = user.id
    room.visitor_creature_id = creature.id
    room.visitor_creature_data = creature.to_dict()
    db.session.commit()
    return jsonify({"success": True, "room_data": _room_payload(room)})


@friend_fight_bp.post("/passerby/match", endpoint="passerby_match")
def passerby_match():
    user = _current_user()
    if not user:
        return jsonify({"success": False, "message": "請先登入再搜尋路人對戰"}), 401

    data = request.get_json(silent=True) or {}
    creature = _creature_for_user(data.get("creature_id"), user.id)
    if not creature:
        return jsonify({"success": False, "message": "找不到你的出戰精靈"}), 400

    player_lat = _safe_float(data.get("lat"))
    player_lng = _safe_float(data.get("lng"))
    force_cpu = bool(data.get("force_cpu"))
    token = str(data.get("match_token") or uuid.uuid4().hex)
    now = time.time()
    _cleanup_passerby_pool(now)

    if force_cpu:
        _PASSERBY_WAITING.pop(token, None)
        cpu_creature = _random_cpu_creature()
        result = _battle_for_player(creature.to_dict(), cpu_creature, random.choice(_CPU_NAMES), "cpu")
        return jsonify({"success": True, "status": "matched", "match_type": "cpu", "battle_result": result})

    if player_lat is None or player_lng is None:
        return jsonify({"success": False, "message": "需要定位資料才能搜尋附近玩家"}), 400

    matched_token = None
    matched_entry = None
    matched_distance = None
    for waiting_token, entry in _PASSERBY_WAITING.items():
        if waiting_token == token or entry.get("user_id") == user.id:
            continue

        distance = _distance_meters(player_lat, player_lng, entry["lat"], entry["lng"])
        if matched_distance is None or distance < matched_distance:
            matched_token = waiting_token
            matched_entry = entry
            matched_distance = distance

    if matched_token and matched_entry:
        _PASSERBY_WAITING.pop(matched_token, None)
        player_result = _battle_for_player(
            creature.to_dict(),
            matched_entry["creature"],
            matched_entry.get("username") or "附近玩家",
            "nearby_player",
        )
        _PASSERBY_RESULTS[matched_token] = _mirror_passerby_result(player_result, user.username)
        return jsonify({
            "success": True,
            "status": "matched",
            "match_type": "nearby_player",
            "distance_meters": round(matched_distance or 0),
            "battle_result": player_result,
        })

    _PASSERBY_WAITING[token] = {
        "token": token,
        "user_id": user.id,
        "username": user.username,
        "lat": player_lat,
        "lng": player_lng,
        "creature": creature.to_dict(),
        "created_at": now,
    }
    return jsonify({
        "success": True,
        "status": "waiting",
        "match_token": token,
        "wait_seconds": _PASSERBY_WAIT_SECONDS,
    })


@friend_fight_bp.get("/passerby/status/<match_token>", endpoint="passerby_status")
def passerby_status(match_token):
    result = _PASSERBY_RESULTS.pop(match_token, None)
    if result:
        return jsonify({
            "success": True,
            "status": "matched",
            "match_type": "nearby_player",
            "battle_result": result,
        })

    _cleanup_passerby_pool()
    if match_token in _PASSERBY_WAITING:
        return jsonify({"success": True, "status": "waiting"})

    return jsonify({"success": True, "status": "expired"})
