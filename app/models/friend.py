from app.extensions import db

class Friend(db.Model):
    __tablename__ = "friends"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    friend_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)

    status = db.Column(db.String(20), default="pending")
    # pending / accepted / blocked
