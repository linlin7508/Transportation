import uuid
from werkzeug.security import generate_password_hash
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    def __init__(self, **kwargs):
        # Ensure an id exists on object creation (useful for tests that
        # inspect `user.id` before DB persist)
        if 'id' not in kwargs or kwargs.get('id') is None:
            kwargs['id'] = str(uuid.uuid4())

        # If caller provided a plaintext password via `password_hash`,
        # hash it so tests and services can rely on `password_hash` being
        # a hashed value. If it's already hashed (werkzeug hash starts
        # with 'pbkdf2:'), leave it as-is.
        pw = kwargs.pop('password_hash', None)
        if pw is not None:
            if isinstance(pw, str) and not pw.startswith('pbkdf2:'):
                pw = generate_password_hash(pw)
            kwargs['password_hash'] = pw

        super().__init__(**kwargs)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)

    # relationship to profile (one‑to‑one)
    profile = db.relationship("Profile", backref="user", uselist=False)
