"""
戰鬥系統 Service Layer
========================
所有戰鬥判定、屬性相剋、道館佔領邏輯集中在此。
Model (arena.py / creature.py) 只負責 Schema 定義。
"""
import random
from app.extensions import db
from app.models.arena import Arena, Battle
from app.models.creature import Creature, ElementType


# ─── 屬性相剋系統 ───────────────────────────────────────

def is_effective_against(attacker_element: ElementType, defender_element: ElementType) -> bool:
    """檢查屬性相剋關係"""
    effectiveness = {
        ElementType.LIGHT: [ElementType.DARK],     # 光克暗
        ElementType.DARK: [ElementType.NORMAL],    # 暗克普
        ElementType.NORMAL: [ElementType.LIGHT],   # 普克光
        ElementType.WATER: [ElementType.FIRE],     # 水克火
        ElementType.FIRE: [ElementType.WOOD],      # 火克草
        ElementType.WOOD: [ElementType.WATER]      # 草克水
    }
    return defender_element in effectiveness.get(attacker_element, [])


def calculate_damage(attacker: Creature, defender: Creature) -> int:
    """計算對目標造成的傷害"""
    base_damage = max(5, attacker.attack)
    
    # 屬性克制加成
    if is_effective_against(attacker.element_type, defender.element_type):
        base_damage = int(base_damage * 1.5)  # 克制加成50%
        
    # 等級差異加成
    level_bonus = max(0, (attacker.level - defender.level) * 0.1)
    final_damage = int(base_damage * (1 + level_bonus))
    
    return max(1, final_damage)


# ─── 回合制戰鬥模擬（保留你原本 fight.py 的隨機戰鬥） ──────

def battle_system(A_atk: float, A_hp: float, A_type: str,
                  B_atk: float, B_hp: float, B_type: str) -> str:
    """回合制戰鬥模擬（來自原始 fight.py）"""
    # 克制對照表
    advantage_map = {
        'water': 'fire',
        'fire': 'grass',  # 注意：grass = wood
        'grass': 'water',
        'wood': 'water',  # 補上 wood 的對應
        'light': 'dark',
        'dark': 'normal',
        'normal': 'light'
    }

    # 屬性克制修正
    if advantage_map.get(A_type) == B_type:
        A_atk *= 1.05
        B_atk *= 0.95
    elif advantage_map.get(B_type) == A_type:
        B_atk *= 1.05
        A_atk *= 0.95

    # 戰鬥回合
    while A_hp > 0 and B_hp > 0:
        turn = random.randint(0, 1)

        if turn == 1:
            damage = A_atk * random.uniform(0.9, 1.1)
            B_hp -= damage
            if B_hp <= 0:
                return "A 勝利"
            damage = B_atk * random.uniform(0.9, 1.1)
            A_hp -= damage
            if A_hp <= 0:
                return "B 勝利"
        else:
            damage = B_atk * random.uniform(0.9, 1.1)
            A_hp -= damage
            if A_hp <= 0:
                return "B 勝利"
            damage = A_atk * random.uniform(0.9, 1.1)
            B_hp -= damage
            if B_hp <= 0:
                return "A 勝利"

    return "平手"


def calculate_battle(host_creature, visitor_creature):
    """計算好友對戰結果（保留原始 fight.py 的完整邏輯）"""
    try:
        host_attack_value = host_creature.get('attack')
        host_hp_value = host_creature.get('hp')
        host_power_value = host_creature.get('power')
        
        if host_attack_value is not None:
            host_attack = float(host_attack_value)
        elif host_power_value is not None:
            host_attack = float(host_power_value)
        else:
            host_attack = 100.0
            
        if host_hp_value is not None:
            host_hp = float(host_hp_value)
        elif host_power_value is not None:
            host_hp = float(host_power_value) * 10
        else:
            host_hp = 1000.0
        
        visitor_attack_value = visitor_creature.get('attack')
        visitor_hp_value = visitor_creature.get('hp')
        visitor_power_value = visitor_creature.get('power')
        
        if visitor_attack_value is not None:
            visitor_attack = float(visitor_attack_value)
        elif visitor_power_value is not None:
            visitor_attack = float(visitor_power_value)
        else:
            visitor_attack = 100.0
            
        if visitor_hp_value is not None:
            visitor_hp = float(visitor_hp_value)
        elif visitor_power_value is not None:
            visitor_hp = float(visitor_power_value) * 10
        else:
            visitor_hp = 1000.0
        
        host_element = (host_creature.get('element_type') or 
                       host_creature.get('type') or 
                       host_creature.get('element') or 'normal')
        host_name = host_creature.get('name', '精靈A')
        
        visitor_element = (visitor_creature.get('element_type') or 
                          visitor_creature.get('type') or 
                          visitor_creature.get('element') or 'normal')
        visitor_name = visitor_creature.get('name', '精靈B')

        host_atk = host_attack * random.uniform(0.8, 1.2)
        host_hp_battle = host_hp * random.uniform(0.9, 1.1)
        visitor_atk = visitor_attack * random.uniform(0.8, 1.2)
        visitor_hp_battle = visitor_hp * random.uniform(0.9, 1.1)
        
        battle_outcome = battle_system(
            A_atk=host_atk, A_hp=host_hp_battle, A_type=host_element.lower(),
            B_atk=visitor_atk, B_hp=visitor_hp_battle, B_type=visitor_element.lower()
        )
        
        if battle_outcome == "A 勝利":
            winner = "host"
            winner_name = host_name
            loser_name = visitor_name
        elif battle_outcome == "B 勝利":
            winner = "visitor"
            winner_name = visitor_name
            loser_name = host_name
        else:
            winner = "draw"
            winner_name = None
            loser_name = None
        
        return {
            'winner': winner,
            'winner_name': winner_name,
            'loser_name': loser_name,
            'battle_details': {
                'host_stats': {
                    'name': host_name,
                    'element': host_element,
                    'attack': host_attack,
                    'hp': host_hp,
                    'final_atk': round(host_atk, 2),
                    'final_hp': round(host_hp_battle, 2)
                },
                'visitor_stats': {
                    'name': visitor_name,
                    'element': visitor_element,
                    'attack': visitor_attack,
                    'hp': visitor_hp,
                    'final_atk': round(visitor_atk, 2),
                    'final_hp': round(visitor_hp_battle, 2)
                },
                'outcome': battle_outcome
            }
        }
        
    except Exception as e:
        return {
            'winner': 'draw',
            'winner_name': None,
            'loser_name': None,
            'battle_details': {
                'error': str(e),
                'outcome': '戰鬥計算失敗'
            }
        }


# ─── 道館佔領邏輯（從 arena.py Model 搬過來） ────────────

def assign_guardian(arena: Arena, creature: Creature) -> bool:
    """設置守護精靈（原本在 Arena Model 裡的 assign_guardian）"""
    if arena.guardian_id == creature.id:
        return False

    if creature.user_id != arena.master_id:
        return False

    if creature.arena_id:
        old_arena = Arena.query.get(creature.arena_id)
        if old_arena:
            old_arena.guardian_id = None
            db.session.add(old_arena)

    arena.guardian_id = creature.id
    creature.arena_id = arena.id
    db.session.add(creature)
    db.session.add(arena)
    return True


def change_master(arena: Arena, new_master_id: int, new_guardian_id: int = None) -> int:
    """變更擂台主人（原本在 Arena Model 裡的 change_master）"""
    old_master_id = arena.master_id
    arena.master_id = new_master_id

    if arena.guardian_id:
        old_guardian = Creature.query.get(arena.guardian_id)
        if old_guardian:
            old_guardian.arena_id = None
            db.session.add(old_guardian)

    if new_guardian_id:
        new_guardian = Creature.query.get(new_guardian_id)
        if new_guardian and new_guardian.user_id == new_master_id:
            arena.guardian_id = new_guardian_id
            new_guardian.arena_id = arena.id
            db.session.add(new_guardian)
    else:
        arena.guardian_id = None

    from datetime import datetime
    arena.last_battle = datetime.utcnow()
    db.session.add(arena)
    return old_master_id


def increase_prestige(arena: Arena, amount: int = 1) -> int:
    """增加擂台聲望值（原本在 Arena Model 裡的 increase_prestige）"""
    arena.prestige += amount
    db.session.add(arena)
    return arena.prestige


def can_challenge(arena: Arena, user_id: int) -> bool:
    """檢查用戶是否可以挑戰此擂台（原本在 Arena Model 裡的 can_challenge）"""
    if user_id == arena.master_id:
        return False
    if arena.guardian_id is None:
        return False
    return True


# ─── 完整戰鬥流程（結合 ORM + 回合制模擬） ────────────────

from app.core.db import transactional

@transactional
def process_fight(arena_id: int, attacker_user_id: int, attacker_creature_id: int):
    """
    處理完整的道館挑戰流程：
    1. 驗證挑戰資格
    2. 執行戰鬥模擬
    3. 如果勝利 → 變更擂台主人
    4. 記錄 Battle 歷史
    """
    arena = Arena.query.get(arena_id)
    if not arena:
        raise ValueError("Arena not found")

    if not can_challenge(arena, attacker_user_id):
        raise ValueError("Cannot challenge this arena")

    attacker_creature = Creature.query.get(attacker_creature_id)
    if not attacker_creature or attacker_creature.user_id != attacker_user_id:
        raise ValueError("Invalid attacker creature")

    defender_user_id = arena.master_id
    defender_creature_id = arena.guardian_id

    if not defender_creature_id:
        # 空城，直接佔領
        change_master(arena, attacker_user_id, attacker_creature_id)
        winner_id = attacker_user_id
        result_text = "win"
    else:
        defender_creature = Creature.query.get(defender_creature_id)

        # 使用回合制戰鬥模擬
        battle_result = battle_system(
            A_atk=float(attacker_creature.attack),
            A_hp=float(attacker_creature.hp),
            A_type=attacker_creature.element_type.value,
            B_atk=float(defender_creature.attack),
            B_hp=float(defender_creature.hp),
            B_type=defender_creature.element_type.value
        )

        if battle_result == "A 勝利":
            result_text = "win"
            winner_id = attacker_user_id
            change_master(arena, attacker_user_id, attacker_creature_id)
        elif battle_result == "B 勝利":
            result_text = "lose"
            winner_id = defender_user_id
            increase_prestige(arena)
        else:
            result_text = "draw"
            winner_id = None

    # 記錄 Battle 歷史
    battle = Battle(
        arena_id=arena_id,
        challenger_id=attacker_user_id,
        defender_id=defender_user_id,
        challenger_creature_id=attacker_creature_id,
        defender_creature_id=defender_creature_id,
        winner_id=winner_id
    )
    db.session.add(battle)

    return result_text
