from functools import wraps
from app.extensions import db

def transactional(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            db.session.commit()
            return result
        except:
            db.session.rollback()
            raise
    return wrapper
