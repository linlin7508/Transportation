import uuid
from app.extensions import db

class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), unique=True)

    avatar = db.Column(db.String(255))
    title = db.Column(db.String(120))
    level = db.Column(db.Integer, default=1)
    exp = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)
    win_count = db.Column(db.Integer, default=0)
    lose_count = db.Column(db.Integer, default=0)
    catch_count = db.Column(db.Integer, default=0)
