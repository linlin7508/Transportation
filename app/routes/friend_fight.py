import random
import string

from flask import Blueprint, g, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.models.creature import Creature
from app.models.friend_fight_room import FriendFightRoom
from app.models.fight import calculate_battle


friend_fight_bp = Blueprint("friend_fight", __name__, url_prefix="/friend-fight")


def _current_user():
    return getattr(g, "user", None)


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
