from datetime import datetime

from sqlalchemy import or_

from app.extensions import db
from app.models.achievement import ACHIEVEMENTS, UserAchievement
from app.models.arena import Arena, Battle
from app.models.creature import Creature
from app.models.friend import Friend
from app.models.friend_fight_room import FriendFightRoom
from app.models.profile import Profile


def _profile_for_user(user_id: str) -> Profile:
    profile = Profile.query.filter_by(user_id=user_id).first()
    if profile:
        return profile

    profile = Profile(user_id=user_id, level=1, exp=0, coins=0, win_count=0, lose_count=0, catch_count=0)
    db.session.add(profile)
    db.session.flush()
    return profile


def _cached_arena_count(user_id: str) -> int:
    from app.routes.game import _load_cached_arenas

    return sum(
        1
        for arena in _load_cached_arenas().values()
        if isinstance(arena, dict) and str(arena.get("ownerPlayerId") or "") == str(user_id)
    )


def _db_arena_count(user_id: str) -> int:
    return Arena.query.filter_by(master_id=user_id).count()


def _battle_count_from_rooms(user_id: str) -> int:
    return FriendFightRoom.query.filter(
        FriendFightRoom.status == "finished",
        FriendFightRoom.battle_result.isnot(None),
        or_(FriendFightRoom.host_user_id == user_id, FriendFightRoom.visitor_user_id == user_id),
    ).count()


def _battle_count_from_arena_records(user_id: str) -> int:
    return Battle.query.filter(or_(Battle.challenger_id == user_id, Battle.defender_id == user_id)).count()


def _friend_count(user_id: str) -> int:
    return Friend.query.filter(
        Friend.status == "accepted",
        or_(Friend.user_id == user_id, Friend.friend_id == user_id),
    ).count()


def _normalize_element(element: str | None) -> str:
    value = (element or "normal").lower()
    if value == "wood":
        return "grass"
    return value


def get_user_stats(user_id: str) -> dict:
    profile = _profile_for_user(user_id)
    creatures = Creature.query.filter_by(user_id=user_id).all()
    captured_count = len(creatures)
    arena_count = _cached_arena_count(user_id) + _db_arena_count(user_id)
    battle_count = max(
        (profile.win_count or 0) + (profile.lose_count or 0),
        _battle_count_from_rooms(user_id) + _battle_count_from_arena_records(user_id),
    )
    win_count = profile.win_count or 0
    lose_count = profile.lose_count or 0
    exp_total = profile.exp or 0
    level = max(profile.level or 1, (exp_total // 100) + 1)
    exp_current = exp_total % 100

    changed = False
    if profile.catch_count != captured_count:
        profile.catch_count = captured_count
        changed = True
    if profile.level != level:
        profile.level = level
        changed = True
    if changed:
        db.session.flush()

    element_counts: dict[str, int] = {}
    for creature in creatures:
        element = _normalize_element(getattr(creature.element_type, "value", creature.element_type))
        element_counts[element] = element_counts.get(element, 0) + 1

    return {
        "level": level,
        "exp": exp_total,
        "exp_current": exp_current,
        "exp_next": 100,
        "exp_progress_percent": exp_current,
        "coins": profile.coins or 0,
        "captured_count": captured_count,
        "arena_count": arena_count,
        "battle_count": battle_count,
        "win_count": win_count,
        "lose_count": lose_count,
        "friend_count": _friend_count(user_id),
        "element_counts": element_counts,
        "distinct_element_count": len(element_counts),
        "distinct_creature_count": len({creature.name for creature in creatures}),
    }


def achievement_progress_for_stats(achievement_id: str, stats: dict) -> int:
    achievement = ACHIEVEMENTS[achievement_id]

    if achievement_id == "ACH-INIT-001":
        return min(stats["captured_count"], 1)
    if achievement_id.startswith("ACH-COLL-") and achievement_id != "ACH-COLL-007":
        return stats["captured_count"]
    if achievement_id == "ACH-COLL-007":
        from app.routes.game import _all_route_creatures

        total_species = len({creature["name"] for creature in _all_route_creatures()})
        return 1 if total_species and stats["distinct_creature_count"] >= total_species else 0
    if achievement_id == "ACH-TYPE-001":
        required = {"fire", "water", "grass", "light", "dark", "normal"}
        return len(required.intersection(stats["element_counts"].keys()))
    if achievement_id.startswith("ACH-TYPE-"):
        element = (achievement.conditions or {}).get("element_type")
        return min(stats["element_counts"].get(_normalize_element(element), 0), achievement.target_value)
    if achievement_id.startswith("ACH-ARENA-"):
        return stats["battle_count"]
    if achievement_id.startswith("ACH-VICTORY-"):
        return stats["win_count"]
    if achievement_id.startswith("ACH-FRIEND-"):
        return stats["friend_count"]
    if achievement_id.startswith("ACH-GYM-"):
        return stats["arena_count"]

    return 0


def sync_user_achievements(user_id: str) -> dict[str, UserAchievement]:
    stats = get_user_stats(user_id)
    records = {
        record.achievement_id: record
        for record in UserAchievement.query.filter_by(user_id=user_id).all()
    }

    for achievement_id, achievement in ACHIEVEMENTS.items():
        progress = min(achievement_progress_for_stats(achievement_id, stats), achievement.target_value)
        record = records.get(achievement_id)

        if record:
            if progress > (record.progress or 0):
                record.progress = progress
            continue

        if progress >= achievement.target_value:
            record = UserAchievement(
                user_id=user_id,
                achievement_id=achievement_id,
                progress=achievement.target_value,
                unlocked_at=datetime.utcnow(),
            )
            db.session.add(record)
            records[achievement_id] = record

    db.session.flush()
    return records


def record_battle_result(user_id: str, won: bool) -> None:
    profile = _profile_for_user(user_id)
    if won:
        profile.win_count = (profile.win_count or 0) + 1
    else:
        profile.lose_count = (profile.lose_count or 0) + 1
