from app.extensions import db
from app.models.arena import Arena

def calculate_level(routes: list) -> int:
    """計算道館等級：根據經過的路線數量"""
    count = len(routes)
    if count >= 3:
        return 3
    elif count == 2:
        return 2
    return 1

def build_arena_from_tdx(stop_data: dict, routes: list) -> Arena:
    """
    將 TDX stop 轉成 Arena ORM
    stop_data 預期包含: name, lat, lon
    """
    lat = stop_data.get("lat") or 0.0
    lon = stop_data.get("lon") or 0.0
    
    arena = Arena(
        name=stop_data.get("name", "未命名站點"),
        latitude=lat,
        longitude=lon,
        level=calculate_level(routes),
        routes=list(set(routes)),  # 去除重複的路線
        challengers=[]
    )

    return arena

def upsert_arena(arena: Arena) -> Arena:
    """
    更新或新增道館，避免重複 (UPSERT)
    """
    existing = Arena.query.filter_by(name=arena.name).first()

    if existing:
        existing.latitude = arena.latitude
        existing.longitude = arena.longitude
        existing.level = arena.level
        existing.routes = arena.routes
        return existing

    db.session.add(arena)
    return arena

def ingest_grouped_stops_to_db(grouped_stops: dict):
    """
    將整理好的 stops (包含對應的多條 routes) 寫入 DB
    """
    for stop_name, data in grouped_stops.items():
        arena = build_arena_from_tdx(
            stop_data={
                "name": stop_name,
                "lat": data["lat"],
                "lon": data["lon"]
            },
            routes=data["routes"]
        )
        upsert_arena(arena)
        
    db.session.commit()
