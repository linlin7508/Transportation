from datetime import datetime

from app.extensions import db


class FriendFightRoom(db.Model):
    __tablename__ = "friend_fight_rooms"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(8), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default="waiting", nullable=False)

    host_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    host_creature_id = db.Column(db.Integer, db.ForeignKey("creatures.id"), nullable=False)
    host_creature_data = db.Column(db.JSON, nullable=False)

    visitor_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    visitor_creature_id = db.Column(db.Integer, db.ForeignKey("creatures.id"), nullable=True)
    visitor_creature_data = db.Column(db.JSON, nullable=True)

    battle_result = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
