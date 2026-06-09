from datetime import date, datetime, timedelta
import uuid

from flask import Blueprint, g, jsonify, render_template, session
from sqlalchemy import func

from app.extensions import db
from app.models.achievement import ACHIEVEMENTS, UserAchievement

daily_migration_bp = Blueprint("daily_migration", __name__, url_prefix="/daily-migration")


class DailyMigration(db.Model):
    __tablename__ = "daily_migrations"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False, index=True)
    migration_date = db.Column(db.Date, nullable=False)
    experience = db.Column(db.Integer, default=100)
    items = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "migration_date", name="uq_daily_migration_user_date"),)


def _current_user_id():
    user = getattr(g, "user", None)
    if user:
        return str(user.id)

    user_id = session.get("user_id") or session.get("user", {}).get("uid")
    if user_id:
        return str(user_id)

    guest_id = session.get("daily_migration_guest_id")
    if not guest_id or str(guest_id).startswith("guest-"):
        guest_id = str(uuid.uuid4())
        session["daily_migration_guest_id"] = guest_id
    return session["daily_migration_guest_id"]


def _has_authenticated_user():
    return bool(getattr(g, "user", None) or session.get("user_id"))


def _migration_rows(user_id):
    return (
        DailyMigration.query
        .filter_by(user_id=user_id)
        .order_by(DailyMigration.migration_date.desc())
        .all()
    )


def _consecutive_days(rows):
    migrated_dates = {row.migration_date for row in rows}
    current = date.today()
    count = 0
    while current in migrated_dates:
        count += 1
        current -= timedelta(days=1)
    return count


def _migration_data(user_id):
    rows = _migration_rows(user_id)
    today = date.today()
    total = len(rows)
    consecutive = _consecutive_days(rows)
    has_today = any(row.migration_date == today for row in rows)
    last_date = rows[0].migration_date.isoformat() if rows else None

    return {
        "has_migrated_today": has_today,
        "total_migrations": total,
        "consecutive_days": consecutive,
        "last_migration_date": last_date,
        "migration_streak": consecutive,
    }


def _unlock_login_achievements(user_id, total_migrations):
    triggered = []
    for achievement_id, achievement in ACHIEVEMENTS.items():
        if not achievement_id.startswith("ACH-LOGIN-"):
            continue
        if total_migrations < achievement.target_value:
            continue

        exists = UserAchievement.query.filter_by(user_id=user_id, achievement_id=achievement_id).first()
        if exists:
            continue

        record = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            progress=achievement.target_value,
        )
        db.session.add(record)
        triggered.append({
            "id": achievement.id,
            "name": achievement.name,
            "description": achievement.description,
            "icon": achievement.icon,
            "reward_points": achievement.reward_points,
        })
    return triggered


@daily_migration_bp.get("", endpoint="daily_migration_page")
def daily_migration_page():
    return render_template("daily_migration/daily_migration.html")


@daily_migration_bp.get("/api/get-migration-status")
def get_migration_status():
    db.create_all()
    user_id = _current_user_id()
    return jsonify({
        "success": True,
        "migration_data": _migration_data(user_id),
    })


@daily_migration_bp.get("/api/get-migration-history")
def get_migration_history():
    db.create_all()
    user_id = _current_user_id()
    rows = _migration_rows(user_id)
    return jsonify({
        "success": True,
        "history": [
            {
                "date": row.migration_date.isoformat(),
                "experience": row.experience,
                "items": row.items or [],
            }
            for row in rows
        ],
    })


@daily_migration_bp.post("/api/perform-migration")
def perform_migration():
    db.create_all()
    user_id = _current_user_id()
    today = date.today()

    existing = DailyMigration.query.filter_by(user_id=user_id, migration_date=today).first()
    if existing:
        return jsonify({
            "success": False,
            "message": "今天已經完成簽到了",
            "migration_data": _migration_data(user_id),
        }), 409

    current_consecutive = _consecutive_days(_migration_rows(user_id))
    bonus_multiplier = min(1 + (current_consecutive * 0.1), 3.0)
    experience = int(100 * bonus_multiplier)
    items = [{"name": "普通藥水碎片", "quantity": 1}]

    db.session.add(DailyMigration(
        user_id=user_id,
        migration_date=today,
        experience=experience,
        items=items,
    ))
    db.session.flush()

    total = db.session.query(func.count(DailyMigration.id)).filter_by(user_id=user_id).scalar() or 0
    triggered_achievements = _unlock_login_achievements(user_id, total) if _has_authenticated_user() else []
    db.session.commit()

    migration_data = _migration_data(user_id)
    return jsonify({
        "success": True,
        "migration_data": migration_data,
        "rewards": {
            "experience": experience,
            "items": items,
            "consecutive_days": migration_data["consecutive_days"],
            "bonus_multiplier": bonus_multiplier,
        },
        "triggered_achievements": triggered_achievements,
    })
