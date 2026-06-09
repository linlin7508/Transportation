"""
精靈管理 Service Layer
========================
精靈的指派、捕獲等邏輯集中在此。
"""
from app.extensions import db
from app.models.creature import Creature
from app.services.creature_images import get_creature_image_url


def assign_creature_to_user(user, creature_data: dict) -> Creature:
    """
    指派一隻新精靈給玩家。
    creature_data 應包含: name, species, element_type, 以及可選的 random_id, hp, attack, image_url
    """
    creature = Creature(
        random_id=creature_data.get("random_id"),
        name=creature_data["name"],
        species=creature_data.get("species", creature_data["name"]),
        element_type=creature_data["element_type"],
        hp=creature_data.get("hp", 100),
        attack=creature_data.get("attack", 10),
        image_url=creature_data.get("image_url") or get_creature_image_url(creature_data["name"]),
        user_id=user.id
    )

    db.session.add(creature)
    db.session.commit()
    return creature
