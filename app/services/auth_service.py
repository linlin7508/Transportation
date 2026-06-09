from app.extensions import db
from app.models.user import User
from app.models.profile import Profile
from werkzeug.security import generate_password_hash, check_password_hash

def register(email, password, username):
    user = User(
        email=email,
        username=username,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.flush()

    profile = Profile(user_id=user.id)
    db.session.add(profile)

    db.session.commit()
    return user


def login(email, password):
    user = User.query.filter_by(email=email).first()
    if not user:
        return None

    if not check_password_hash(user.password_hash, password):
        return None

    return user
