from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, redirect, url_for, session
from app.extensions import db
from app.models.achievement import (
    ACHIEVEMENTS,
    CATEGORY_DISPLAY_NAMES,
    CATEGORY_ICONS,
    UserAchievement,
)

achievement_bp = Blueprint("achievement", __name__, url_prefix="/achievement")


def _firebase_config():
    return {
        "apiKey": "",
        "authDomain": "",
        "projectId": "",
        "storageBucket": "",
        "messagingSenderId": "",
        "appId": "",
    }


@achievement_bp.get("", endpoint="achievement_page")
def achievement_page():
    if "user" not in session:
        session["user"] = {"uid": session.get("user_id", ""), "username": "訪客訓練師"}
    return render_template("achievement/achievement.html", firebase_config=_firebase_config(), is_demo=False)


@achievement_bp.get("/demo", endpoint="achievement_demo")
def achievement_demo():
    if "user" not in session:
        session["user"] = {"uid": session.get("user_id", "demo"), "username": "Demo"}
    return render_template("achievement/achievement.html", firebase_config=_firebase_config(), is_demo=True)


@achievement_bp.get("/demo-logout", endpoint="demo_logout")
def demo_logout():
    return redirect(url_for("achievement.achievement_page"))


@achievement_bp.get("/summary", endpoint="summary")
def summary():
    return render_template("achievement/summary.html")


@achievement_bp.get("/api/user_achievements")
def user_achievements():
    user_id = str(session.get("user_id") or session.get("user", {}).get("uid") or "")
    user_records = {}
    if user_id:
        records = UserAchievement.query.filter_by(user_id=user_id).all()
        user_records = {record.achievement_id: record for record in records}

    categories = {}
    completed_count = 0
    recent_count = 0
    recent_threshold = datetime.utcnow() - timedelta(days=7)

    for achievement_id, achievement in ACHIEVEMENTS.items():
        record = user_records.get(achievement_id)
        completed = record is not None
        progress = record.progress if record else 0
        completed_at = None

        if completed:
            completed_count += 1
            if record.unlocked_at:
                completed_at = int(record.unlocked_at.timestamp())
                if record.unlocked_at >= recent_threshold:
                    recent_count += 1

        category_key = achievement.category.value
        categories.setdefault(category_key, {
            "display_name": CATEGORY_DISPLAY_NAMES.get(achievement.category, category_key),
            "icon": CATEGORY_ICONS.get(achievement.category, "fas fa-star"),
            "achievements": [],
        })

        categories[category_key]["achievements"].append({
            "id": achievement.id,
            "name": achievement.name,
            "description": achievement.description,
            "completed": completed,
            "progress": achievement.target_value if completed else min(progress, achievement.target_value),
            "target_value": achievement.target_value,
            "reward_points": achievement.reward_points,
            "icon": achievement.icon,
            "hidden": achievement.hidden,
            "completed_at": completed_at,
        })

    total = len(ACHIEVEMENTS)
    completion_rate = round((completed_count / total * 100), 1) if total else 0

    return jsonify({
        "status": "success",
        "stats": {
            "total": total,
            "completed": completed_count,
            "completion_rate": completion_rate,
            "recent": recent_count,
        },
        "categories": categories,
    })

@achievement_bp.get("/api/demo_achievements")
def demo_achievements():
    return user_achievements()
