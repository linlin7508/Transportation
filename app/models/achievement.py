"""
成就系統模型
定義遊戲中的各種成就類型和數據結構
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any
import time
import uuid
from app.extensions import db

class AchievementCategory(Enum):
    """成就類別"""
    INIT = "init"           # 初次邂逅
    TYPE = "type"           # 屬性蒐集
    COLLECTION = "collection"  # 精靈蒐集數量
    ARENA = "arena"         # 競技場對戰
    VICTORY = "victory"     # 競技場勝利
    FRIEND = "friend"       # 交友
    GYM = "gym"            # 道館佔領
    LOGIN = "login"         # 登入天數
    SPECIAL = "special"     # 特殊成就

class AchievementType(Enum):
    """成就觸發類型"""
    COUNT = "count"         # 數量型（捕捉X隻精靈）
    VARIETY = "variety"     # 種類型（捕捉所有屬性）
    STREAK = "streak"       # 連續型（連續登入X天）
    MILESTONE = "milestone" # 里程碑型（達到某個特定條件）
    SPECIAL_EVENT = "special_event"  # 特殊事件型

@dataclass
class Achievement:
    """成就定義"""
    id: str
    category: AchievementCategory
    type: AchievementType
    name: str
    description: str
    icon: str
    target_value: int = 1
    conditions: Dict[str, Any] = None
    reward_points: int = 10
    hidden: bool = False

# 成就定義表
ACHIEVEMENTS = {
    # 🐣 初次邂逅
    "ACH-INIT-001": Achievement(
        id="ACH-INIT-001",
        category=AchievementCategory.INIT,
        type=AchievementType.MILESTONE,
        name="Hello world",
        description="與你的第一隻精靈相遇。",
        icon="fas fa-baby",
        target_value=1,
        reward_points=50
    ),

    # 🧩 屬性蒐集成就
    "ACH-TYPE-001": Achievement(
        id="ACH-TYPE-001",
        category=AchievementCategory.TYPE,
        type=AchievementType.VARIETY,
        name="我全都要",
        description="蒐集所有屬性精靈各一隻。",
        icon="fas fa-rainbow",
        target_value=6,
        conditions={"element_types": ["fire", "water", "grass", "light", "dark", "normal"]},
        reward_points=200
    ),
    "ACH-TYPE-002": Achievement(
        id="ACH-TYPE-002",
        category=AchievementCategory.TYPE,
        type=AchievementType.COUNT,
        name="草：一種日文",
        description="蒐集所有草屬性精靈。",
        icon="fas fa-leaf",
        target_value=1,
        conditions={"element_type": "grass", "collect_all": True},
        reward_points=100
    ),
    "ACH-TYPE-003": Achievement(
        id="ACH-TYPE-003",
        category=AchievementCategory.TYPE,
        type=AchievementType.COUNT,
        name="咕嚕咕嚕",
        description="蒐集所有水屬性精靈。",
        icon="fas fa-tint",
        target_value=1,
        conditions={"element_type": "water", "collect_all": True},
        reward_points=100
    ),
    "ACH-TYPE-004": Achievement(
        id="ACH-TYPE-004",
        category=AchievementCategory.TYPE,
        type=AchievementType.COUNT,
        name="熱愛105度的你",
        description="蒐集所有火屬性精靈。",
        icon="fas fa-fire",
        target_value=1,
        conditions={"element_type": "fire", "collect_all": True},
        reward_points=100
    ),
    "ACH-TYPE-005": Achievement(
        id="ACH-TYPE-005",
        category=AchievementCategory.TYPE,
        type=AchievementType.COUNT,
        name="正道的光",
        description="蒐集所有光屬性精靈。",
        icon="fas fa-sun",
        target_value=1,
        conditions={"element_type": "light", "collect_all": True},
        reward_points=100
    ),
    "ACH-TYPE-006": Achievement(
        id="ACH-TYPE-006",
        category=AchievementCategory.TYPE,
        type=AchievementType.COUNT,
        name="黑暗之子",
        description="蒐集所有暗屬性精靈。",
        icon="fas fa-moon",
        target_value=1,
        conditions={"element_type": "dark", "collect_all": True},
        reward_points=100
    ),
    "ACH-TYPE-007": Achievement(
        id="ACH-TYPE-007",
        category=AchievementCategory.TYPE,
        type=AchievementType.COUNT,
        name="普通Disco",
        description="蒐集所有普通屬性精靈。",
        icon="fas fa-circle",
        target_value=1,
        conditions={"element_type": "normal", "collect_all": True},
        reward_points=100
    ),

    # 📦 精靈蒐集數量成就
    "ACH-COLL-001": Achievement(
        id="ACH-COLL-001",
        category=AchievementCategory.COLLECTION,
        type=AchievementType.COUNT,
        name="更上一層樓",
        description="蒐集 10 隻精靈。",
        icon="fas fa-layer-group",
        target_value=10,
        reward_points=50
    ),
    "ACH-COLL-002": Achievement(
        id="ACH-COLL-002",
        category=AchievementCategory.COLLECTION,
        type=AchievementType.COUNT,
        name="更上二層樓",
        description="蒐集 20 隻精靈。",
        icon="fas fa-layer-group",
        target_value=20,
        reward_points=75
    ),
    "ACH-COLL-003": Achievement(
        id="ACH-COLL-003",
        category=AchievementCategory.COLLECTION,
        type=AchievementType.COUNT,
        name="更上三層樓",
        description="蒐集 30 隻精靈。",
        icon="fas fa-layer-group",
        target_value=30,
        reward_points=100
    ),
    "ACH-COLL-004": Achievement(
        id="ACH-COLL-004",
        category=AchievementCategory.COLLECTION,
        type=AchievementType.COUNT,
        name="更上四層樓",
        description="蒐集 40 隻精靈。",
        icon="fas fa-layer-group",
        target_value=40,
        reward_points=125
    ),
    "ACH-COLL-005": Achievement(
        id="ACH-COLL-005",
        category=AchievementCategory.COLLECTION,
        type=AchievementType.COUNT,
        name="更上五層樓",
        description="蒐集 50 隻精靈。",
        icon="fas fa-layer-group",
        target_value=50,
        reward_points=150
    ),
    "ACH-COLL-006": Achievement(
        id="ACH-COLL-006",
        category=AchievementCategory.COLLECTION,
        type=AchievementType.COUNT,
        name="更上六層樓",
        description="蒐集 60 隻精靈。",
        icon="fas fa-layer-group",
        target_value=60,
        reward_points=175
    ),
    "ACH-COLL-007": Achievement(
        id="ACH-COLL-007",
        category=AchievementCategory.COLLECTION,
        type=AchievementType.MILESTONE,
        name="世界的真理，我已解明",
        description="蒐集所有精靈。",
        icon="fas fa-crown",
        target_value=1,
        conditions={"collect_all_creatures": True},
        reward_points=500
    ),

    # ⚔️ 競技場對戰成就
    "ACH-ARENA-001": Achievement(
        id="ACH-ARENA-001",
        category=AchievementCategory.ARENA,
        type=AchievementType.MILESTONE,
        name="牛刀小試",
        description="參與一次競技場對戰。",
        icon="fas fa-sword",
        target_value=1,
        reward_points=30
    ),
    "ACH-ARENA-002": Achievement(
        id="ACH-ARENA-002",
        category=AchievementCategory.ARENA,
        type=AchievementType.COUNT,
        name="熱血沸騰",
        description="累積參與 10 次競技場對戰。",
        icon="fas fa-fire-alt",
        target_value=10,
        reward_points=100
    ),
    "ACH-ARENA-003": Achievement(
        id="ACH-ARENA-003",
        category=AchievementCategory.ARENA,
        type=AchievementType.COUNT,
        name="好戰分子",
        description="累積參與 50 次競技場對戰。",
        icon="fas fa-fist-raised",
        target_value=50,
        reward_points=200
    ),
    "ACH-ARENA-004": Achievement(
        id="ACH-ARENA-004",
        category=AchievementCategory.ARENA,
        type=AchievementType.COUNT,
        name="沉浸在戰鬥的藝術中",
        description="累積參與 100 次競技場對戰。",
        icon="fas fa-chess",
        target_value=100,
        reward_points=300
    ),

    # 🏆 競技場勝利成就
    "ACH-VICTORY-001": Achievement(
        id="ACH-VICTORY-001",
        category=AchievementCategory.VICTORY,
        type=AchievementType.MILESTONE,
        name="勝利的果實",
        description="勝出一場競技場對戰。",
        icon="fas fa-trophy",
        target_value=1,
        reward_points=50
    ),
    "ACH-VICTORY-002": Achievement(
        id="ACH-VICTORY-002",
        category=AchievementCategory.VICTORY,
        type=AchievementType.COUNT,
        name="我一個打十個",
        description="累積勝出 10 場競技場對戰。",
        icon="fas fa-medal",
        target_value=10,
        reward_points=150
    ),
    "ACH-VICTORY-003": Achievement(
        id="ACH-VICTORY-003",
        category=AchievementCategory.VICTORY,
        type=AchievementType.COUNT,
        name="還有誰？",
        description="累積勝出 50 場競技場對戰。",
        icon="fas fa-crown",
        target_value=50,
        reward_points=300
    ),
    "ACH-VICTORY-004": Achievement(
        id="ACH-VICTORY-004",
        category=AchievementCategory.VICTORY,
        type=AchievementType.COUNT,
        name="他簡直是戰神",
        description="累積勝出 100 場競技場對戰。",
        icon="fas fa-crown",
        target_value=100,
        reward_points=500
    ),

    # 👥 交友成就
    "ACH-FRIEND-001": Achievement(
        id="ACH-FRIEND-001",
        category=AchievementCategory.FRIEND,
        type=AchievementType.MILESTONE,
        name="不認識怎麼說話？",
        description="結交一名好友。",
        icon="fas fa-user-plus",
        target_value=1,
        reward_points=30
    ),
    "ACH-FRIEND-002": Achievement(
        id="ACH-FRIEND-002",
        category=AchievementCategory.FRIEND,
        type=AchievementType.COUNT,
        name="不說話怎麼認識？",
        description="結交 10 名好友。",
        icon="fas fa-users",
        target_value=10,
        reward_points=100
    ),
    "ACH-FRIEND-003": Achievement(
        id="ACH-FRIEND-003",
        category=AchievementCategory.FRIEND,
        type=AchievementType.COUNT,
        name="四海之內皆兄弟",
        description="結交 50 名好友。",
        icon="fas fa-globe",
        target_value=50,
        reward_points=200
    ),
    "ACH-FRIEND-004": Achievement(
        id="ACH-FRIEND-004",
        category=AchievementCategory.FRIEND,
        type=AchievementType.COUNT,
        name="天下誰人不識君？",
        description="結交 100 名好友。",
        icon="fas fa-star",
        target_value=100,
        reward_points=300
    ),

    # 🏛️ 道館佔領成就
    "ACH-GYM-001": Achievement(
        id="ACH-GYM-001",
        category=AchievementCategory.GYM,
        type=AchievementType.MILESTONE,
        name="此路由我開",
        description="成功佔領一個道館。",
        icon="fas fa-flag",
        target_value=1,
        reward_points=50
    ),
    "ACH-GYM-002": Achievement(
        id="ACH-GYM-002",
        category=AchievementCategory.GYM,
        type=AchievementType.COUNT,
        name="此樹由我栽",
        description="成功佔領兩個道館。",
        icon="fas fa-tree",
        target_value=2,
        reward_points=100
    ),
    "ACH-GYM-003": Achievement(
        id="ACH-GYM-003",
        category=AchievementCategory.GYM,
        type=AchievementType.COUNT,
        name="要從此地過",
        description="成功佔領三個道館。",
        icon="fas fa-road",
        target_value=3,
        reward_points=150
    ),
    "ACH-GYM-004": Achievement(
        id="ACH-GYM-004",
        category=AchievementCategory.GYM,
        type=AchievementType.COUNT,
        name="留下買路財",
        description="成功佔領四個道館。",
        icon="fas fa-coins",
        target_value=4,
        reward_points=200
    ),

    # 📅 登入天數成就
    "ACH-LOGIN-001": Achievement(
        id="ACH-LOGIN-001",
        category=AchievementCategory.LOGIN,
        type=AchievementType.MILESTONE,
        name="感謝每一次相遇",
        description="累計登入 1 天。",
        icon="fas fa-calendar-day",
        target_value=1,
        reward_points=10
    ),
    "ACH-LOGIN-002": Achievement(
        id="ACH-LOGIN-002",
        category=AchievementCategory.LOGIN,
        type=AchievementType.COUNT,
        name="感恩每一段緣分",
        description="累計登入 7 天。",
        icon="fas fa-calendar-week",
        target_value=7,
        reward_points=50
    ),
    "ACH-LOGIN-003": Achievement(
        id="ACH-LOGIN-003",
        category=AchievementCategory.LOGIN,
        type=AchievementType.COUNT,
        name="珍惜旅途的風景",
        description="累計登入 30 天。",
        icon="fas fa-calendar-alt",
        target_value=30,
        reward_points=150
    ),
    "ACH-LOGIN-004": Achievement(
        id="ACH-LOGIN-004",
        category=AchievementCategory.LOGIN,
        type=AchievementType.COUNT,
        name="期待每一個明天",
        description="累計登入 60 天。",
        icon="fas fa-calendar",
        target_value=60,
        reward_points=200
    ),
    "ACH-LOGIN-005": Achievement(
        id="ACH-LOGIN-005",
        category=AchievementCategory.LOGIN,
        type=AchievementType.COUNT,
        name="阿偉你麼還在打電動？",
        description="累計登入 100 天。",
        icon="fas fa-gamepad",
        target_value=100,
        reward_points=300
    ),

    # ✨ 特殊成就
    "ACH-SPEC-001": Achievement(
        id="ACH-SPEC-001",
        category=AchievementCategory.SPECIAL,
        type=AchievementType.SPECIAL_EVENT,
        name="在轉動的地球再次相遇",
        description="超過 14 天未上線後再次登入。",
        icon="fas fa-globe-americas",
        target_value=1,
        conditions={"days_offline": 14},
        reward_points=100
    ),
}

def get_achievements_by_category() -> Dict[str, List[Achievement]]:
    """按類別分組成就"""
    categories = {}
    for achievement in ACHIEVEMENTS.values():
        category_name = achievement.category.value
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append(achievement)
    return categories

def get_achievement_by_id(achievement_id: str) -> Achievement:
    """根據ID獲取成就"""
    return ACHIEVEMENTS.get(achievement_id)

# 類別顯示名稱映射
CATEGORY_DISPLAY_NAMES = {
    AchievementCategory.INIT: "初次邂逅",
    AchievementCategory.TYPE: "屬性蒐集",
    AchievementCategory.COLLECTION: "精靈蒐集",
    AchievementCategory.ARENA: "競技場對戰",
    AchievementCategory.VICTORY: "競技場勝利",
    AchievementCategory.FRIEND: "交友",
    AchievementCategory.GYM: "道館佔領",
    AchievementCategory.LOGIN: "登入天數",
    AchievementCategory.SPECIAL: "特殊成就"
}

# 類別圖標映射
CATEGORY_ICONS = {
    AchievementCategory.INIT: "fas fa-baby",
    AchievementCategory.TYPE: "fas fa-palette",
    AchievementCategory.COLLECTION: "fas fa-archive",
    AchievementCategory.ARENA: "fas fa-swords",
    AchievementCategory.VICTORY: "fas fa-trophy",
    AchievementCategory.FRIEND: "fas fa-users",
    AchievementCategory.GYM: "fas fa-university",
    AchievementCategory.LOGIN: "fas fa-calendar",
    AchievementCategory.SPECIAL: "fas fa-star"
}


# SQLAlchemy ORM Models
class UserAchievement(db.Model):
    """用戶成就記錄"""
    __tablename__ = "user_achievements"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    achievement_id = db.Column(db.String(50), nullable=False)  # References ACHIEVEMENTS dict key
    unlocked_at = db.Column(db.DateTime, default=db.func.now())
    progress = db.Column(db.Integer, default=0)  # For tracking progress towards achievement
    
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),)
