from flask import Blueprint, jsonify, render_template, request
from app.services.creature_images import get_creature_image_url

friend_fight_bp = Blueprint("friend_fight", __name__, url_prefix="/friend-fight")


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
    return jsonify({"success": True, "room_id": "DEMO1234"})


@friend_fight_bp.get("/room/<room_id>/status", endpoint="room_status")
def room_status(room_id):
    return jsonify({"success": True, "room_id": room_id, "status": "waiting"})


@friend_fight_bp.post("/start-battle", endpoint="start_battle")
def start_battle():
    data = request.get_json(silent=True) or {}
    return jsonify({"success": True, "data": data})


@friend_fight_bp.post("/room/<room_id>/delete", endpoint="delete_room")
def delete_room(room_id):
    return jsonify({"success": True, "room_id": room_id})


@friend_fight_bp.get("/visitor/<room_id>", endpoint="visitor_fight")
def visitor_fight(room_id):
    return render_template("friend_fight/visitor_fight.html", room_id=room_id)


@friend_fight_bp.post("/join-room", endpoint="join_room")
def join_room():
    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    return jsonify({
        "success": bool(room_id),
        "room_data": {
            "room_id": room_id or "",
            "host_creature": {
                "name": "虛弱兔",
                "element": "Normal",
                "image_url": get_creature_image_url("虛弱兔"),
                "attack": 100,
                "hp": 1000,
            },
        },
    })


@friend_fight_bp.post("/confirm-join", endpoint="confirm_join")
def confirm_join():
    data = request.get_json(silent=True) or {}
    return jsonify({"success": True, "data": data})
