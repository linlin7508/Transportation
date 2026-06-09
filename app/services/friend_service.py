from app.models.friend import Friend
from app.models.user import User
from app.extensions import db

def add_friend(requester: User, friend_id_str: str):
    """Create a pending friend request.
    Args:
        requester: User object of the user sending the request.
        friend_id_str: UUID string of the user to be added as a friend.
    Returns:
        Friend instance or None if target user not found.
    """
    try:
        friend_user = User.query.get(friend_id_str)
    except Exception:
        friend_user = None
    if not friend_user:
        return None
    # Prevent duplicate or self‑friendship
    if friend_user.id == requester.id:
        return None
    existing = Friend.query.filter_by(user_id=requester.id, friend_id=friend_user.id).first()
    if existing:
        return existing
    f = Friend(user_id=requester.id, friend_id=friend_user.id, status="pending")
    db.session.add(f)
    db.session.commit()
    return f

def accept_friend(user: User, request_id: int):
    """Accept a pending friend request.
    Args:
        user: The user who is accepting.
        request_id: Primary key of the Friend row.
    Returns:
        Updated Friend instance or None.
    """
    f = Friend.query.filter_by(id=request_id, friend_id=user.id, status="pending").first()
    if not f:
        return None
    f.status = "accepted"
    db.session.commit()
    return f

def decline_friend(user: User, request_id: int):
    """Decline (delete) a pending friend request."""
    f = Friend.query.filter_by(id=request_id, friend_id=user.id, status="pending").first()
    if not f:
        return None
    db.session.delete(f)
    db.session.commit()
    return True

def remove_friend(user: User, friend_id_str: str):
    """Remove an existing friendship (both directions)."""
    try:
        target_id = friend_id_str
    except Exception:
        return None
    # Delete any record where either side matches
    f = Friend.query.filter(
        ((Friend.user_id == user.id) & (Friend.friend_id == target_id)) |
        ((Friend.user_id == target_id) & (Friend.friend_id == user.id))
    ).first()
    if not f:
        return None
    db.session.delete(f)
    db.session.commit()
    return True
