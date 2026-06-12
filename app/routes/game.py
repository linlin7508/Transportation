import csv
import hashlib
import json
import random
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote, unquote

from flask import Blueprint, g, jsonify, request, render_template, session

from app.extensions import db
from app.models.arena import Arena
from app.models.creature import Creature, ElementType
from app.models.profile import Profile
from app.services.creature_images import CREATURE_IMAGE_URLS, get_creature_image_url

game_bp = Blueprint("game", __name__, url_prefix="/game")
_CREATURE_CSV = Path(__file__).resolve().parents[1] / "data" / "creatures" / "current_creatures.csv"
_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_USER_FAVORITES_FILE = _DATA_DIR / "user_favorites.json"
_BUS_DATA_FILES = {
    "cat-right-route": _DATA_DIR / "routes" / "cat_right_route.json",
    "cat-left-route": _DATA_DIR / "routes" / "cat_left_route.json",
    "cat-left-zhinan-route": _DATA_DIR / "routes" / "cat_left_zhinan_route.json",
    "brown-3-route": _DATA_DIR / "routes" / "brown_3_route.json",
    "cat-right-stops": _DATA_DIR / "stops" / "cat_right_stops.json",
    "cat-left-stops": _DATA_DIR / "stops" / "cat_left_stops.json",
    "cat-left-zhinan-stops": _DATA_DIR / "stops" / "cat_left_zhinan_stops.json",
    "brown-3-stops": _DATA_DIR / "stops" / "brown_3_stops.json",
}
_ARENA_LEVELS_FILE = _DATA_DIR / "arenas" / "arena_levels.json"
_ARENA_LEVELS_BACKUP_FILE = _DATA_DIR / "arenas" / "arena_levels_backup_1750129920.json"
_DEFAULT_ROUTE_POSITIONS = [
    ("cat-right", "貓空右線", "cat-right-route", 25.0330, 121.5654),
    ("cat-left", "貓空左線(動物園)", "cat-left-route", 25.0298, 121.5761),
    ("cat-left-zhinan", "貓空左線(指南宮)", "cat-left-zhinan-route", 25.0355, 121.5815),
    ("brown-3", "棕3路線", "brown-3-route", 25.0205, 121.5420),
]
_CSV_ROUTE_ALIASES = {
    "cat_right_route": "cat-right",
    "cat-right-route": "cat-right",
    "cat-right": "cat-right",
    "貓空右線": "cat-right",
    "cat_left_route": "cat-left",
    "cat-left-route": "cat-left",
    "cat-left": "cat-left",
    "貓空左線(動物園)": "cat-left",
    "cat_left_zhinan_route": "cat-left-zhinan",
    "cat-left-zhinan-route": "cat-left-zhinan",
    "cat-left-zhinan": "cat-left-zhinan",
    "貓空左線(指南宮)": "cat-left-zhinan",
    "br3_route": "brown-3",
    "brown_3_route": "brown-3",
    "brown-3-route": "brown-3",
    "brown-3": "brown-3",
    "棕3": "brown-3",
    "棕3路線": "brown-3",
}
_ROUTE_META_BY_ID = {route_id: meta for meta in _DEFAULT_ROUTE_POSITIONS for route_id in [meta[0]]}
_BACKPACK_DEFAULTS = {
    "normal": {"count": 1000, "success_rate": 0.45},
    "advanced": {"count": 1000, "success_rate": 0.65},
    "premium": {"count": 1000, "success_rate": 0.85},
}
_CAPTURE_RATES_BY_RARITY = {
    "premium": {"SSR": 0.5, "SR": 0.8, "R": 1.0, "N": 1.0},
    "advanced": {"SSR": 0.25, "SR": 0.5, "R": 0.8, "N": 1.0},
    "normal": {"SSR": 0.0, "SR": 0.25, "R": 0.5, "N": 0.8},
}
_BACKPACK_VERSION = 2
_BACKPACK_ITEM_ALIASES = {
    "magic_circle_normal": "normal",
    "normal_magic_circle": "normal",
    "magic-circle-normal": "normal",
    "magic_circle_advanced": "advanced",
    "advanced_magic_circle": "advanced",
    "magic-circle-advanced": "advanced",
    "magic_circle_premium": "premium",
    "premium_magic_circle": "premium",
    "magic_circle_legendary": "premium",
    "legendary_magic_circle": "premium",
    "magic-circle-premium": "premium",
}
_ROUTE_CREATURE_SPAWNS: list[dict] = []
_ROUTE_CREATURE_LAST_SPAWN_AT = 0.0
_ROUTE_CREATURE_SPAWN_LOCK = threading.Lock()
_USER_FAVORITES_LOCK = threading.Lock()
_ROUTE_CREATURE_SPAWN_INTERVAL = 30
_ROUTE_CREATURE_LIFETIME = 5 * 60
_ROUTE_CREATURES_PER_ROUTE = 2


def _default_backpack() -> dict:
    return {key: value.copy() for key, value in _BACKPACK_DEFAULTS.items()}


def _normalize_backpack_item(item_name: str | None) -> str:
    normalized = (item_name or "").strip()
    return _BACKPACK_ITEM_ALIASES.get(normalized, normalized)


def _capture_rate(circle_type: str | None, rarity: str | None) -> float:
    circle = _normalize_backpack_item(circle_type)
    normalized_rarity = str(rarity or "N").strip().upper()
    return float(_CAPTURE_RATES_BY_RARITY.get(circle, {}).get(normalized_rarity, 0.0))


def _session_backpack() -> dict:
    backpack = session.get("game_backpack")
    if not isinstance(backpack, dict) or session.get("game_backpack_version") != _BACKPACK_VERSION:
        backpack = _default_backpack()

    defaults = _default_backpack()
    for item_name, item_defaults in defaults.items():
        current = backpack.get(item_name)
        if not isinstance(current, dict):
            current = {}

        item = {**item_defaults, **current}
        try:
            item["count"] = max(0, int(item.get("count", 0)))
        except (TypeError, ValueError):
            item["count"] = item_defaults["count"]
        backpack[item_name] = item

    session["game_backpack"] = backpack
    session["game_backpack_version"] = _BACKPACK_VERSION
    session.modified = True
    return backpack


def _load_cached_arenas() -> dict:
    for arena_file in (_ARENA_LEVELS_FILE, _ARENA_LEVELS_BACKUP_FILE):
        try:
            with arena_file.open(encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
            print(f"載入道館快取失敗 {arena_file}: {error}")
            continue

        if isinstance(data, dict):
            return data

    return {}


def _write_cached_arenas(arenas: dict) -> None:
    _ARENA_LEVELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = _ARENA_LEVELS_FILE.with_suffix(".json.tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(arenas, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_file.replace(_ARENA_LEVELS_FILE)


def _normalize_arena_payload(arena: dict) -> dict:
    normalized = dict(arena)
    position = normalized.get("position")
    if isinstance(position, list) and len(position) >= 2:
        normalized["position"] = position
        normalized["position_array"] = position
        normalized["position_object"] = {"lat": position[0], "lng": position[1]}
    elif isinstance(position, dict):
        normalized["position"] = position
        normalized["position_array"] = [position.get("lat"), position.get("lng")]

    stop_ids = normalized.get("stopIds") or normalized.get("stop_ids") or []
    normalized["stopIds"] = stop_ids
    normalized["stop_ids"] = stop_ids
    normalized["stopName"] = normalized.get("stopName") or normalized.get("name", "").removesuffix("道館")
    normalized["owner"] = normalized.get("owner") or normalized.get("master_name")
    owner_creature = normalized.get("ownerCreature") or normalized.get("owner_creature") or normalized.get("guardian")
    normalized["ownerCreature"] = owner_creature
    normalized["owner_creature"] = owner_creature
    level = int(normalized.get("level") or 1)
    rewards = normalized.get("rewards")
    if not isinstance(rewards, dict) or "available_rewards" not in rewards:
        rewards = {
            "available_rewards": [
                {
                    "type": "experience",
                    "quantity": 10 * level,
                    "description": f"道館經驗值 +{10 * level}",
                }
            ],
            "claimed": False,
        }
    normalized["rewards"] = rewards
    return normalized


def _arena_available_rewards(arena: dict) -> list[dict]:
    normalized = _normalize_arena_payload(arena)
    rewards = normalized.get("rewards") or {}
    available = rewards.get("available_rewards")
    if isinstance(available, list):
        return available
    return []


def _creature_score(creature_data: dict) -> int:
    attack = int(creature_data.get("attack") or creature_data.get("power") or 10)
    hp = int(creature_data.get("hp") or 100)
    level = int(creature_data.get("level") or 1)
    return attack * 2 + hp + level * 5


def _db_arena_to_game_payload(arena: Arena) -> dict:
    data = arena.to_dict()
    guardian = data.get("guardian")
    return _normalize_arena_payload({
        "id": data["id"],
        "name": data["name"],
        "position": {"lat": data.get("latitude"), "lng": data.get("longitude")},
        "stopIds": [str(arena.bus_stop_id)] if arena.bus_stop_id else [],
        "stopName": data.get("bus_stop") or data["name"].removesuffix("道館"),
        "routes": data.get("routes") or [],
        "level": data.get("level") or 1,
        "owner": data.get("master_name"),
        "ownerPlayerId": data.get("master_id"),
        "ownerCreature": guardian,
        "challengers": data.get("challengers") or [],
        "prestige": data.get("prestige") or 0,
    })


def _find_cached_arena(arena_id_or_name: str) -> dict | None:
    query = unquote(str(arena_id_or_name)).strip()
    arenas = _load_cached_arenas()
    arena = arenas.get(query)
    if arena:
        return _normalize_arena_payload(arena)

    for item in arenas.values():
        if not isinstance(item, dict):
            continue
        names = {
            str(item.get("id") or ""),
            str(item.get("name") or ""),
            str(item.get("stopName") or ""),
            f"{item.get('stopName')}道館" if item.get("stopName") else "",
        }
        if query in names:
            return _normalize_arena_payload(item)

    return None


def _find_cached_arena_key(arena_id_or_name: str) -> str | None:
    query = unquote(str(arena_id_or_name)).strip()
    arenas = _load_cached_arenas()
    if query in arenas:
        return query

    for arena_id, item in arenas.items():
        if not isinstance(item, dict):
            continue
        names = {
            str(item.get("id") or ""),
            str(item.get("name") or ""),
            str(item.get("stopName") or ""),
            f"{item.get('stopName')}道館" if item.get("stopName") else "",
        }
        if query in names:
            return arena_id

    return None


def _offset_position(index: int, base_lat: float, base_lng: float) -> dict[str, float]:
    row = index // 9
    col = index % 9
    return {
        "lat": round(base_lat + ((row % 5) - 2) * 0.0018, 6),
        "lng": round(base_lng + (col - 4) * 0.0018, 6),
    }


def _route_meta(index: int) -> tuple[str, str, str, float, float]:
    return _DEFAULT_ROUTE_POSITIONS[index % len(_DEFAULT_ROUTE_POSITIONS)]


def _route_meta_from_csv_route(route_value: str | None, index: int) -> tuple[str, str, str, float, float]:
    route_key = (route_value or "").strip()
    route_id = _CSV_ROUTE_ALIASES.get(route_key)
    if route_id and route_id in _ROUTE_META_BY_ID:
        return _ROUTE_META_BY_ID[route_id]
    return _route_meta(index)


def _csv_route_id(route_value: str | None) -> str | None:
    return _CSV_ROUTE_ALIASES.get((route_value or "").strip())


def _int_or_none(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _value_from_range(value, min_value, max_value, fallback: int, randomize: bool) -> int:
    parsed_value = _int_or_none(value)
    if parsed_value is not None:
        return parsed_value

    parsed_min = _int_or_none(min_value)
    parsed_max = _int_or_none(max_value)
    if parsed_min is not None and parsed_max is not None:
        low, high = sorted((parsed_min, parsed_max))
        return random.randint(low, high) if randomize else high

    return fallback


def _route_point(route_file_key: str, index: int) -> dict[str, float] | None:
    try:
        points = _load_bus_data(route_file_key)
    except (FileNotFoundError, KeyError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"載入路線座標失敗 {route_file_key}: {error}")
        return None

    coordinates = []
    for point in points:
        try:
            lat = float(point.get("PositionLat"))
            lng = float(point.get("PositionLon"))
        except (AttributeError, TypeError, ValueError):
            continue

        coordinates.append({"lat": round(lat, 6), "lng": round(lng, 6)})

    if not coordinates:
        return None

    # 用質數步長分散精靈，避免全部擠在路線前段，同時保持結果穩定。
    return coordinates[(index * 17) % len(coordinates)]


def _route_coordinates(route_file_key: str) -> list[dict[str, float]]:
    try:
        points = _load_bus_data(route_file_key)
    except (FileNotFoundError, KeyError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"載入路線座標失敗 {route_file_key}: {error}")
        return []

    coordinates = []
    for point in points:
        try:
            lat = float(point.get("PositionLat"))
            lng = float(point.get("PositionLon"))
        except (AttributeError, TypeError, ValueError):
            continue

        coordinates.append({"lat": round(lat, 6), "lng": round(lng, 6)})

    return coordinates


def _random_route_position(route_file_key: str, base_lat: float, base_lng: float) -> dict[str, float]:
    coordinates = _route_coordinates(route_file_key)
    if coordinates:
        return random.choice(coordinates)
    return _offset_position(random.randint(0, 99), base_lat, base_lng)


def _route_position(index: int, route_file_key: str, base_lat: float, base_lng: float) -> dict[str, float]:
    return _route_point(route_file_key, index) or _offset_position(index, base_lat, base_lng)


def _normalize_creature_payload(creature: dict, index: int = 0, randomize_stats: bool = False) -> dict:
    name = (creature.get("name") or creature.get("C_Name") or "虛弱兔").strip()
    raw_csv_route = creature.get("route") or creature.get("Route")
    csv_route_id = _csv_route_id(raw_csv_route)
    route_id, route_name, route_file_key, base_lat, base_lng = _route_meta_from_csv_route(
        raw_csv_route,
        index,
    )
    route_id = creature.get("route_id") or route_id
    route_name = creature.get("route_name") or route_name
    if raw_csv_route and not csv_route_id and not creature.get("route_id"):
        route_id = "unassigned"
        route_name = "未指定路線"
    lat = creature.get("lat") or creature.get("latitude")
    lng = creature.get("lng") or creature.get("lon") or creature.get("longitude")

    try:
        position = {"lat": float(lat), "lng": float(lng)}
    except (TypeError, ValueError):
        position = _route_position(index, route_file_key, base_lat, base_lng)

    image_url = creature.get("image_url") or get_creature_image_url(name)
    hp_min = _int_or_none(creature.get("hp_min") or creature.get("HP_Min"))
    hp_max = _int_or_none(creature.get("hp_max") or creature.get("HP_Max"))
    attack_min = _int_or_none(creature.get("attack_min") or creature.get("ATK_Min"))
    attack_max = _int_or_none(creature.get("attack_max") or creature.get("ATK_Max"))

    return {
        "id": creature.get("id") or creature.get("ID") or f"data-{index + 1}",
        "source_id": creature.get("source_id"),
        "name": name,
        "en_name": creature.get("en_name") or creature.get("EN_Name") or "",
        "type": creature.get("type") or creature.get("Type") or creature.get("element_type") or "normal",
        "element_type": creature.get("element_type") or creature.get("type") or creature.get("Type") or "normal",
        "rate": creature.get("rate") or creature.get("Rate") or "N",
        "rarity": creature.get("rarity") or creature.get("Rate") or creature.get("rate") or "N",
        "hp": _value_from_range(creature.get("hp"), hp_min, hp_max, 100, randomize_stats),
        "hp_min": hp_min,
        "hp_max": hp_max,
        "attack": _value_from_range(creature.get("attack"), attack_min, attack_max, 10, randomize_stats),
        "attack_min": attack_min,
        "attack_max": attack_max,
        "route": creature.get("Route") or creature.get("route") or "",
        "route_id": route_id,
        "route_name": route_name,
        "position": position,
        "lat": position["lat"],
        "lng": position["lng"],
        "image_url": image_url,
        "img": image_url,
    }


def _creatures_from_images() -> list[dict]:
    creatures = []
    creature_names = [
        name for name in sorted(CREATURE_IMAGE_URLS.keys())
        if name != "home" and not name.startswith("people")
    ]
    for index, name in enumerate(creature_names):
        route_id, route_name, route_file_key, base_lat, base_lng = _route_meta(index)
        position = _route_position(index, route_file_key, base_lat, base_lng)
        creatures.append(_normalize_creature_payload({
            "id": f"img-{index + 1}",
            "name": name,
            "route_id": route_id,
            "route_name": route_name,
            "lat": position["lat"],
            "lng": position["lng"],
        }, index))
    return creatures


def _creatures_from_csv() -> list[dict]:
    if not _CREATURE_CSV.exists():
        return []

    with _CREATURE_CSV.open(newline="", encoding="utf-8-sig") as csv_file:
        rows = list(csv.DictReader(csv_file))

    return [
        _normalize_creature_payload(row, index)
        for index, row in enumerate(rows)
        if row.get("name") or row.get("C_Name")
    ]


def _all_route_creatures() -> list[dict]:
    return _creatures_from_csv() or _creatures_from_images()


def _route_creature_source_by_id(source_id: str) -> dict | None:
    decoded_source_id = unquote(str(source_id))
    return next(
        (
            creature for creature in _all_route_creatures()
            if str(creature.get("id")) == decoded_source_id
        ),
        None,
    )


def _spawn_route_creature_id(route_id: str, source_id: str, now: float) -> str:
    encoded_route_id = quote(str(route_id), safe="")
    encoded_source_id = quote(str(source_id), safe="")
    return f"spawn~{encoded_route_id}~{encoded_source_id}~{int(now)}~{uuid.uuid4().hex[:8]}"


def _spawn_route_creature(source: dict, route_id: str, route_name: str, route_file_key: str, base_lat: float, base_lng: float, now: float) -> dict:
    position = _random_route_position(route_file_key, base_lat, base_lng)
    source_id = str(source.get("id") or "")
    spawned = _normalize_creature_payload({
        **source,
        "id": _spawn_route_creature_id(route_id, source_id, now),
        "route_id": route_id,
        "route_name": route_name,
        "lat": position["lat"],
        "lng": position["lng"],
        "hp": None,
        "attack": None,
    }, randomize_stats=True)
    spawned["source_id"] = source_id
    spawned["spawned_at"] = now
    spawned["expires_at"] = now + _ROUTE_CREATURE_LIFETIME
    spawned["lifetime_seconds"] = _ROUTE_CREATURE_LIFETIME
    return spawned


def _active_route_creature_spawns(spawn_if_due: bool = True) -> list[dict]:
    global _ROUTE_CREATURE_LAST_SPAWN_AT

    now = time.time()
    with _ROUTE_CREATURE_SPAWN_LOCK:
        _ROUTE_CREATURE_SPAWNS[:] = [
            creature for creature in _ROUTE_CREATURE_SPAWNS
            if float(creature.get("expires_at") or 0) > now
        ]

        if spawn_if_due and now - _ROUTE_CREATURE_LAST_SPAWN_AT >= _ROUTE_CREATURE_SPAWN_INTERVAL:
            source_creatures = _all_route_creatures()
            if source_creatures:
                for route_id, route_name, route_file_key, base_lat, base_lng in _DEFAULT_ROUTE_POSITIONS:
                    route_sources = [
                        creature for creature in source_creatures
                        if creature.get("route_id") == route_id
                    ]
                    if not route_sources:
                        continue
                    for _ in range(_ROUTE_CREATURES_PER_ROUTE):
                        source = random.choice(route_sources)
                        _ROUTE_CREATURE_SPAWNS.append(
                            _spawn_route_creature(source, route_id, route_name, route_file_key, base_lat, base_lng, now)
                        )
                _ROUTE_CREATURE_LAST_SPAWN_AT = now

        return [dict(creature) for creature in _ROUTE_CREATURE_SPAWNS]


def _find_route_creature(creature_id: str) -> dict | None:
    decoded_id = unquote(str(creature_id))
    creature = next(
        (
            item for item in [*_active_route_creature_spawns(spawn_if_due=False), *_all_route_creatures()]
            if str(item["id"]) == decoded_id or item["name"] == decoded_id
        ),
        None,
    )
    if creature:
        return creature

    return _missing_spawn_creature_from_id(decoded_id)


def _missing_spawn_creature_from_id(creature_id: str) -> dict | None:
    if creature_id.startswith("spawn~"):
        return _missing_current_spawn_creature_from_id(creature_id)
    if creature_id.startswith("spawn-"):
        return _missing_legacy_spawn_creature_from_id(creature_id)
    return None


def _missing_current_spawn_creature_from_id(creature_id: str) -> dict | None:
    spawn_parts = creature_id.split("~")
    if len(spawn_parts) != 5:
        return None

    _prefix, encoded_route_id, encoded_source_id, spawned_at, _spawn_suffix = spawn_parts
    route_id = unquote(encoded_route_id)
    source_id = unquote(encoded_source_id)
    try:
        spawned_at_float = float(spawned_at)
    except (TypeError, ValueError):
        return None

    if time.time() - spawned_at_float > _ROUTE_CREATURE_LIFETIME + 300:
        return None

    source = _route_creature_source_by_id(source_id)
    if not source:
        return None

    return _normalize_creature_payload({
        **source,
        "id": creature_id,
        "route_id": route_id,
        "source_id": source_id,
    }, randomize_stats=True)


def _missing_legacy_spawn_creature_from_id(creature_id: str) -> dict | None:
    spawn_parts = creature_id.removeprefix("spawn-").rsplit("-", 2)
    if len(spawn_parts) != 3:
        return None

    route_id, spawned_at, _spawn_suffix = spawn_parts
    try:
        spawned_at_float = float(spawned_at)
    except (TypeError, ValueError):
        return None

    if time.time() - spawned_at_float > _ROUTE_CREATURE_LIFETIME + 300:
        return None

    route_sources = [
        creature for creature in _all_route_creatures()
        if creature.get("route_id") == route_id
    ]
    if not route_sources:
        return None

    digest = hashlib.sha256(creature_id.encode("utf-8")).hexdigest()
    source = route_sources[int(digest, 16) % len(route_sources)]
    return _normalize_creature_payload({
        **source,
        "id": creature_id,
        "route_id": route_id,
    }, randomize_stats=True)


def _remove_route_creature_spawn(creature_id: str) -> None:
    with _ROUTE_CREATURE_SPAWN_LOCK:
        _ROUTE_CREATURE_SPAWNS[:] = [
            creature for creature in _ROUTE_CREATURE_SPAWNS
            if str(creature.get("id")) != str(creature_id)
        ]


def _element_type(value: str | None) -> ElementType:
    normalized = (value or "normal").strip().lower()
    aliases = {
        "grass": "wood",
        "earth": "wood",
        "土系": "wood",
        "草系": "wood",
        "火系": "fire",
        "水系": "water",
        "光系": "light",
        "暗系": "dark",
        "一般": "normal",
        "普通": "normal",
    }
    normalized = aliases.get(normalized, normalized)

    try:
        return ElementType(normalized)
    except ValueError:
        return ElementType.NORMAL


def _load_user_favorites() -> dict:
    try:
        with _USER_FAVORITES_FILE.open(encoding="utf-8") as file:
            favorites = json.load(file)
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return {}

    return favorites if isinstance(favorites, dict) else {}


def _write_user_favorites(favorites: dict) -> None:
    _USER_FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = _USER_FAVORITES_FILE.with_suffix(".json.tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(favorites, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_file.replace(_USER_FAVORITES_FILE)


def _favorite_creature_ids(user_id: str) -> set[int]:
    with _USER_FAVORITES_LOCK:
        favorites = _load_user_favorites()

    if not isinstance(favorites, dict):
        return set()

    raw_ids = favorites.get(str(user_id), [])
    if not isinstance(raw_ids, list):
        return set()

    favorite_ids = set()
    for creature_id in raw_ids:
        try:
            favorite_ids.add(int(creature_id))
        except (TypeError, ValueError):
            continue
    return favorite_ids


def _set_favorite_creature_ids(user_id: str, favorite_ids: set[int]) -> None:
    with _USER_FAVORITES_LOCK:
        favorites = _load_user_favorites()
        favorites[str(user_id)] = sorted(favorite_ids)
        _write_user_favorites(favorites)


def _creature_dict_with_favorite(creature: Creature, favorite_ids: set[int]) -> dict:
    payload = creature.to_dict()
    payload["favorite"] = creature.id in favorite_ids
    return payload


def _normalized_type(value: str | None) -> str:
    normalized = (value or "normal").strip().lower()
    aliases = {
        "grass": "wood",
        "earth": "wood",
        "土": "wood",
        "木": "wood",
        "草": "wood",
        "土系": "wood",
        "木系": "wood",
        "草系": "wood",
        "火": "fire",
        "火系": "fire",
        "水": "water",
        "水系": "water",
        "光": "light",
        "光系": "light",
        "暗": "dark",
        "暗系": "dark",
        "一般": "normal",
        "普通": "normal",
    }
    return aliases.get(normalized, normalized)


def _type_multiplier(attacker_type: str | None, defender_type: str | None) -> float:
    attacker = _normalized_type(attacker_type)
    defender = _normalized_type(defender_type)
    strong_against = {
        "water": "fire",
        "fire": "wood",
        "wood": "water",
    }

    if {attacker, defender} == {"light", "dark"}:
        return 1.2
    if strong_against.get(attacker) == defender:
        return 1.2
    if strong_against.get(defender) == attacker:
        return 0.8
    return 1.0


def _critical_rate(creature_data: dict) -> float:
    rarity = str(
        creature_data.get("rate")
        or creature_data.get("rarity")
        or creature_data.get("species")
        or "N"
    ).strip().upper()
    return {
        "N": 0.1,
        "R": 0.2,
        "SR": 0.3,
        "SSR": 0.4,
    }.get(rarity, 0.1)


def _battle_damage(attacker: dict, defender: dict) -> dict:
    attack = int(attacker.get("attack") or attacker.get("power") or 10)
    multiplier = _type_multiplier(
        attacker.get("element_type") or attacker.get("type") or attacker.get("element"),
        defender.get("element_type") or defender.get("type") or defender.get("element"),
    )
    critical_rate = _critical_rate(attacker)
    is_critical = random.random() < critical_rate
    damage = round(attack * multiplier * (2 if is_critical else 1), 2)
    return {
        "damage": damage,
        "base_attack": attack,
        "type_multiplier": multiplier,
        "critical": is_critical,
        "critical_rate": critical_rate,
    }


def _battle_result(challenger: dict, defender: dict) -> dict:
    challenger_damage = _battle_damage(challenger, defender)
    defender_damage = _battle_damage(defender, challenger)
    challenger_hp = int(challenger.get("hp") or 100)
    defender_hp = int(defender.get("hp") or 100)
    challenger_score = challenger_hp + challenger_damage["damage"]
    defender_score = defender_hp + defender_damage["damage"]

    return {
        "is_win": challenger_score >= defender_score,
        "challenger": {
            **challenger_damage,
            "hp": challenger_hp,
            "score": round(challenger_score, 2),
        },
        "defender": {
            **defender_damage,
            "hp": defender_hp,
            "score": round(defender_score, 2),
        },
    }


def _current_user_payload(user) -> dict:
    profile = Profile.query.filter_by(user_id=user.id).first()
    return {
        "id": user.id,
        "uid": user.id,
        "email": user.email,
        "username": user.username,
        "level": profile.level if profile else 1,
        "experience": profile.exp if profile else 0,
    }


def _load_bus_data(file_key: str) -> list[dict]:
    data_file = _BUS_DATA_FILES[file_key]
    with data_file.open(encoding="utf-8") as file:
        payload = json.load(file)
    data = payload.get("data", payload if isinstance(payload, list) else [])

    if file_key == "brown-3-route" and not data:
        stops = _load_bus_data("brown-3-stops")
        return [
            {
                "PositionLat": stop["StopPosition"]["PositionLat"],
                "PositionLon": stop["StopPosition"]["PositionLon"],
            }
            for stop in sorted(stops, key=lambda item: int(item.get("StopSequence") or 0))
            if stop.get("StopPosition")
        ]

    return data


@game_bp.get("/catch")
def catch():
    return render_template("game/catch.html")


@game_bp.get("/fullscreen-map")
def fullscreen_map():
    return render_template("game/map.html")


@game_bp.get("/battle")
@game_bp.get("/battle/<int:arena_id>")
def battle(arena_id=None):
    return render_template("game/battle.html", arena_id=arena_id)


@game_bp.get("/api/bus/<file_key>")
def bus_data(file_key):
    if file_key not in _BUS_DATA_FILES:
        return jsonify({"success": False, "message": "bus data not found"}), 404

    return jsonify(_load_bus_data(file_key))


@game_bp.get("/api/bus/live/<route_key>")
def live_bus_positions(route_key):
    from app.services.tdx_service import fetch_live_bus_positions

    route_aliases = {
        "br3": "brown-3",
        "brown_3": "brown-3",
        "brown-3": "brown-3",
        "cat_right": "cat-right",
        "cat-right": "cat-right",
        "cat_left": "cat-left",
        "cat-left": "cat-left",
        "cat_left_zhinan": "cat-left-zhinan",
        "cat-left-zhinan": "cat-left-zhinan",
    }
    normalized_route = route_aliases.get(route_key)
    if not normalized_route:
        return jsonify({"success": False, "message": "unsupported bus route", "buses": []}), 404

    buses, error = fetch_live_bus_positions(normalized_route)
    return jsonify({
        "success": error is None,
        "source": "tdx-live" if error is None else "tdx-live-error",
        "route": normalized_route,
        "count": len(buses),
        "buses": buses,
        "message": error,
    })


@game_bp.get("/api/arena/cached-levels")
def cached_arena_levels():
    arenas = {
        arena_id: _normalize_arena_payload(arena)
        for arena_id, arena in _load_cached_arenas().items()
        if isinstance(arena, dict)
    }
    return jsonify({"success": True, "arenas": arenas, "count": len(arenas)})


@game_bp.get("/api/arena/get-by-name/<path:arena_name>")
def get_arena_by_name(arena_name):
    arena = _find_cached_arena(arena_name)
    if arena:
        return jsonify({"success": True, "arena": arena})

    db_arena = Arena.query.filter_by(name=unquote(arena_name)).first()
    if db_arena:
        return jsonify({"success": True, "arena": _db_arena_to_game_payload(db_arena)})

    return jsonify({"success": False, "message": "arena not found"}), 404


@game_bp.get("/api/arena/check/<path:arena_name>")
def check_arena(arena_name):
    arena = _find_cached_arena(arena_name)
    if arena:
        return jsonify({"success": True, "exists": True, "arena": arena})

    db_arena = Arena.query.filter_by(name=unquote(arena_name)).first()
    if db_arena:
        return jsonify({"success": True, "exists": True, "arena": _db_arena_to_game_payload(db_arena)})

    return jsonify({"success": True, "exists": False, "arena": None})


@game_bp.post("/api/arena/check-exists")
def check_arena_exists():
    payload = request.get_json(silent=True) or {}
    arena_name = payload.get("name") or ""
    arena = _find_cached_arena(arena_name)
    if arena:
        return jsonify({"success": True, "exists": True, "arena": arena})

    db_arena = Arena.query.filter_by(name=arena_name).first()
    if db_arena:
        return jsonify({"success": True, "exists": True, "arena": _db_arena_to_game_payload(db_arena)})

    return jsonify({"success": True, "exists": False, "arena": None})


@game_bp.post("/api/arena/save")
def save_arena():
    payload = request.get_json(silent=True) or {}
    arena_id = str(payload.get("id") or "").strip()
    if not arena_id:
        return jsonify({"success": False, "message": "missing arena id"}), 400

    arenas = _load_cached_arenas()
    arenas[arena_id] = {**arenas.get(arena_id, {}), **payload}
    _write_cached_arenas(arenas)
    return jsonify({"success": True, "arena": _normalize_arena_payload(arenas[arena_id])})


@game_bp.post("/api/arena/update-routes")
def update_arena_routes():
    payload = request.get_json(silent=True) or {}
    arena_id = str(payload.get("arenaId") or payload.get("arena_id") or "").strip()
    route_name = str(payload.get("routeName") or payload.get("route_name") or "").strip()
    if not arena_id or not route_name:
        return jsonify({"success": False, "message": "missing arenaId or routeName"}), 400

    arenas = _load_cached_arenas()
    arena = arenas.get(arena_id)
    if not isinstance(arena, dict):
        return jsonify({"success": False, "message": "arena not found"}), 404

    routes = arena.get("routes") if isinstance(arena.get("routes"), list) else []
    if route_name not in routes:
        routes.append(route_name)
    arena["routes"] = routes
    arena["level"] = max(1, len(routes))
    arenas[arena_id] = arena
    _write_cached_arenas(arenas)
    return jsonify({"success": True, "arena": _normalize_arena_payload(arena)})


@game_bp.get("/capture-interactive/<path:creature_id>")
def capture_interactive(creature_id):
    decoded_id = unquote(creature_id)
    creature = _find_route_creature(decoded_id)
    if creature is None:
        creature = _normalize_creature_payload({"id": decoded_id, "name": decoded_id or "虛弱兔"})

    return render_template("game/capture_interactive.html", creature=creature)


@game_bp.get("/api/route-creatures/get-from-csv")
def route_creatures_from_csv():
    creatures = _all_route_creatures()
    return jsonify({"success": True, "creatures": creatures, "count": len(creatures)})


@game_bp.get("/api/route-creatures/get-all")
def route_creatures_all():
    creatures = _active_route_creature_spawns()
    return jsonify({
        "success": True,
        "creatures": creatures,
        "count": len(creatures),
        "spawn_interval_seconds": _ROUTE_CREATURE_SPAWN_INTERVAL,
        "lifetime_seconds": _ROUTE_CREATURE_LIFETIME,
        "per_route": _ROUTE_CREATURES_PER_ROUTE,
    })


@game_bp.get("/api/user/backpack")
def user_backpack():
    return jsonify({"success": True, "backpack": _session_backpack()})


@game_bp.post("/api/user/verify-auth-status")
def verify_auth_status():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "unauthorized"}), 401

    return jsonify({"success": True, **_current_user_payload(user)})


@game_bp.get("/api/user/get-current")
def current_user():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "unauthorized"}), 401

    user_data = _current_user_payload(user)
    return jsonify({"success": True, **user_data, "user_data": user_data})


@game_bp.get("/api/user/addition")
def user_addition():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "unauthorized"}), 401

    return jsonify({"success": True, "addition": 1.0})


@game_bp.post("/api/user/backpack/update")
def update_user_backpack():
    payload = request.get_json(silent=True) or {}
    item_name = _normalize_backpack_item(payload.get("item_name"))

    if item_name not in _BACKPACK_DEFAULTS:
        return jsonify({
            "success": False,
            "message": "unknown backpack item",
            "item_name": payload.get("item_name"),
        }), 400

    try:
        count_change = int(payload.get("count_change", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "count_change must be an integer"}), 400

    backpack = _session_backpack()
    current_count = int(backpack[item_name].get("count", 0))
    backpack[item_name]["count"] = max(0, current_count + count_change)
    session["game_backpack"] = backpack
    session.modified = True

    return jsonify({
        "success": True,
        "backpack": backpack,
        "item_name": item_name,
        "item": backpack[item_name],
    })


@game_bp.post("/api/capture-interactive")
def capture_interactive_api():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "請先登入再進行捕捉操作"}), 401

    payload = request.get_json(silent=True) or {}
    creature_id = str(payload.get("creatureId") or payload.get("creature_id") or "").strip()
    circle_type = _normalize_backpack_item(payload.get("circleType") or payload.get("circle_type") or "premium")
    if not creature_id:
        return jsonify({"success": False, "message": "missing creatureId"}), 400
    if circle_type not in _CAPTURE_RATES_BY_RARITY:
        return jsonify({"success": False, "message": "未知的魔法陣類型"}), 400

    route_creature = _find_route_creature(creature_id)
    if route_creature is None:
        return jsonify({"success": False, "message": "creature not found"}), 404

    rarity = route_creature.get("rate") or route_creature.get("rarity") or route_creature.get("species") or "N"
    capture_rate = _capture_rate(circle_type, rarity)
    roll = random.random()
    if roll >= capture_rate:
        return jsonify({
            "success": False,
            "captured": False,
            "message": "捕捉失敗",
            "circle_type": circle_type,
            "rarity": rarity,
            "capture_rate": capture_rate,
            "roll": round(roll, 6),
        })

    creature = Creature(
        random_id=uuid.uuid4().hex,
        name=route_creature["name"],
        species=rarity,
        element_type=_element_type(route_creature.get("element_type") or route_creature.get("type")),
        level=1,
        experience=0,
        hp=int(route_creature.get("hp") or 100),
        attack=int(route_creature.get("attack") or 10),
        image_url=route_creature.get("image_url") or get_creature_image_url(route_creature["name"]),
        user_id=user.id,
        captured_players=user.id,
    )
    db.session.add(creature)

    experience_gained = 20
    profile = Profile.query.filter_by(user_id=user.id).first()
    if profile:
        profile.catch_count = (profile.catch_count or 0) + 1
        profile.exp = (profile.exp or 0) + experience_gained
        profile.level = max(profile.level or 1, (profile.exp // 100) + 1)

    db.session.commit()
    _remove_route_creature_spawn(creature_id)

    return jsonify({
        "success": True,
        "captured": True,
        "message": "捕捉成功",
        "circle_type": circle_type,
        "rarity": rarity,
        "capture_rate": capture_rate,
        "roll": round(roll, 6),
        "creature": creature.to_dict(),
        "user_level_info": {
            "experience_gained": experience_gained,
            "current_experience": profile.exp if profile else 0,
            "new_level": profile.level if profile else 1,
        },
    })


@game_bp.get("/api/user/creatures")
def user_creatures():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    favorite_ids = _favorite_creature_ids(user.id)
    creatures = Creature.query.filter_by(user_id=user.id).all()
    return jsonify([_creature_dict_with_favorite(creature, favorite_ids) for creature in creatures])


@game_bp.post("/api/user/creatures/<int:creature_id>/toggle-favorite")
def toggle_creature_favorite(creature_id: int):
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "請先登入"}), 401

    creature = db.session.get(Creature, creature_id)
    if not creature:
        return jsonify({"success": False, "message": "找不到指定精靈"}), 404
    if creature.user_id != user.id:
        return jsonify({"success": False, "message": "這隻精靈不屬於目前登入使用者"}), 403

    favorite_ids = _favorite_creature_ids(user.id)
    if creature_id in favorite_ids:
        favorite_ids.remove(creature_id)
        favorite = False
        message = "已移出我的最愛"
    else:
        favorite_ids.add(creature_id)
        favorite = True
        message = "已加入我的最愛"

    _set_favorite_creature_ids(user.id, favorite_ids)
    return jsonify({
        "success": True,
        "favorite": favorite,
        "message": message,
        "creature": _creature_dict_with_favorite(creature, favorite_ids),
    })


@game_bp.get("/api/arena-battle/get-user-creatures")
def arena_battle_user_creatures():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "unauthorized"}), 401

    favorite_ids = _favorite_creature_ids(user.id)
    creatures = Creature.query.filter_by(user_id=user.id).all()
    return jsonify({
        "success": True,
        "creatures": [_creature_dict_with_favorite(creature, favorite_ids) for creature in creatures],
    })


@game_bp.get("/api/arena-battle/get-arena/<path:arena_id>")
def arena_battle_get_arena(arena_id):
    cached_arena = _find_cached_arena(arena_id)
    if cached_arena:
        return jsonify({"success": True, "arena": cached_arena})

    try:
        db_arena_id = int(arena_id)
    except (TypeError, ValueError):
        db_arena_id = None

    if db_arena_id is not None:
        db_arena = db.session.get(Arena, db_arena_id)
        if db_arena:
            return jsonify({"success": True, "arena": _db_arena_to_game_payload(db_arena)})

    return jsonify({"success": False, "message": "arena not found"}), 404


@game_bp.post("/api/arena-battle/occupy")
def arena_battle_occupy():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "請先登入再佔領道館"}), 401

    payload = request.get_json(silent=True) or {}
    arena_id = str(payload.get("arena_id") or payload.get("arenaId") or "").strip()
    creature_id = payload.get("creature_id") or payload.get("creatureId")
    if not arena_id or creature_id in (None, ""):
        return jsonify({"success": False, "message": "缺少道館或精靈資料"}), 400

    try:
        creature_id_int = int(creature_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "精靈 ID 格式錯誤"}), 400

    creature = db.session.get(Creature, creature_id_int)
    if not creature:
        return jsonify({"success": False, "message": "找不到要派出的精靈"}), 404
    if creature.user_id != user.id:
        return jsonify({"success": False, "message": "這隻精靈不屬於目前登入使用者"}), 403

    arena_key = _find_cached_arena_key(arena_id)
    if arena_key:
        arenas = _load_cached_arenas()
        arena = arenas.get(arena_key)
        if not isinstance(arena, dict):
            return jsonify({"success": False, "message": "道館資料格式錯誤"}), 500

        if arena.get("owner") and arena.get("ownerPlayerId") != user.id:
            return jsonify({"success": False, "message": "道館已被其他玩家佔領，請改用挑戰"}), 400

        creature_payload = creature.to_dict()
        arena["owner"] = user.username
        arena["ownerPlayerId"] = user.id
        arena["ownerCreature"] = creature_payload
        arena["owner_creature"] = creature_payload
        arenas[arena_key] = arena
        _write_cached_arenas(arenas)

        return jsonify({
            "success": True,
            "message": "成功佔領道館",
            "arena": _normalize_arena_payload(arena),
        })

    try:
        db_arena_id = int(arena_id)
    except (TypeError, ValueError):
        db_arena_id = None

    if db_arena_id is None:
        return jsonify({"success": False, "message": "找不到指定道館"}), 404

    arena = db.session.get(Arena, db_arena_id)
    if not arena:
        return jsonify({"success": False, "message": "找不到指定道館"}), 404
    if arena.master_id and arena.master_id != user.id:
        return jsonify({"success": False, "message": "道館已被其他玩家佔領，請改用挑戰"}), 400

    arena.master_id = user.id
    arena.guardian_id = creature.id
    creature.arena_id = arena.id
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "成功佔領道館",
        "arena": _db_arena_to_game_payload(arena),
    })


@game_bp.post("/api/arena-battle/battle")
def arena_battle_battle():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "請先登入再挑戰道館"}), 401

    payload = request.get_json(silent=True) or {}
    arena_id = str(payload.get("arena_id") or payload.get("arenaId") or "").strip()
    creature_id = payload.get("creature_id") or payload.get("creatureId")
    if not arena_id or creature_id in (None, ""):
        return jsonify({"success": False, "message": "缺少道館或精靈資料"}), 400

    try:
        creature_id_int = int(creature_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "精靈 ID 格式錯誤"}), 400

    challenger = db.session.get(Creature, creature_id_int)
    if not challenger:
        return jsonify({"success": False, "message": "找不到挑戰精靈"}), 404
    if challenger.user_id != user.id:
        return jsonify({"success": False, "message": "這隻精靈不屬於目前登入使用者"}), 403

    arena_key = _find_cached_arena_key(arena_id)
    if arena_key:
        arenas = _load_cached_arenas()
        arena = arenas.get(arena_key)
        if not isinstance(arena, dict):
            return jsonify({"success": False, "message": "道館資料格式錯誤"}), 500
        if not arena.get("owner") or not arena.get("ownerCreature"):
            return jsonify({"success": False, "message": "此道館尚無擂主，請直接佔領"}), 400
        if arena.get("ownerPlayerId") == user.id:
            return jsonify({"success": False, "message": "不能挑戰自己佔領的道館"}), 400

        defender = arena.get("ownerCreature") or {}
        battle_detail = _battle_result(challenger.to_dict(), defender)
        is_win = battle_detail["is_win"]
        if is_win:
            creature_payload = challenger.to_dict()
            arena["owner"] = user.username
            arena["ownerPlayerId"] = user.id
            arena["ownerCreature"] = creature_payload
            arena["owner_creature"] = creature_payload
            message = "挑戰成功！你已成為新的道館擂主。"
        else:
            challengers = arena.get("challengers") if isinstance(arena.get("challengers"), list) else []
            challengers.append({"user_id": user.id, "username": user.username, "creature_id": challenger.id})
            arena["challengers"] = challengers[-20:]
            message = "挑戰失敗，守護精靈成功守住道館。"

        arenas[arena_key] = arena
        _write_cached_arenas(arenas)
        return jsonify({
            "success": True,
            "is_win": is_win,
            "result": is_win,
            "message": message,
            "battle": battle_detail,
            "arena": _normalize_arena_payload(arena),
        })

    return jsonify({"success": False, "message": "找不到指定道館"}), 404


@game_bp.post("/api/arena-battle/collect-rewards")
def arena_battle_collect_rewards():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "請先登入再領取獎勵"}), 401

    payload = request.get_json(silent=True) or {}
    arena_id = str(payload.get("arena_id") or payload.get("arenaId") or "").strip()
    if not arena_id:
        return jsonify({"success": False, "message": "缺少道館資料"}), 400

    arena_key = _find_cached_arena_key(arena_id)
    if arena_key:
        arenas = _load_cached_arenas()
        arena = arenas.get(arena_key)
        if not isinstance(arena, dict):
            return jsonify({"success": False, "message": "道館資料格式錯誤"}), 500
        if arena.get("ownerPlayerId") != user.id:
            return jsonify({"success": False, "message": "只有目前擂主可以領取獎勵"}), 403

        collected_items = _arena_available_rewards(arena)
        if not collected_items:
            return jsonify({"success": False, "message": "目前沒有可領取的獎勵"}), 400

        profile = Profile.query.filter_by(user_id=user.id).first()
        experience = sum(int(item.get("quantity") or 0) for item in collected_items if item.get("type") == "experience")
        if profile and experience:
            profile.exp = (profile.exp or 0) + experience
            profile.level = max(profile.level or 1, (profile.exp // 100) + 1)

        arena["rewards"] = {"available_rewards": [], "claimed": True}
        arenas[arena_key] = arena
        _write_cached_arenas(arenas)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "成功領取獎勵",
            "collected_items": collected_items,
            "arena": _normalize_arena_payload(arena),
        })

    return jsonify({"success": False, "message": "找不到指定道館"}), 404
