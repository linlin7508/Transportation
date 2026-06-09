from datetime import datetime
import enum
from app.extensions import db
from app.services.creature_images import get_creature_image_url

class ElementType(enum.Enum):
    """精靈元素類型"""
    FIRE = "fire"      # 火系
    WATER = "water"    # 水系
    WOOD = "wood"      # 草系
    LIGHT = "light"    # 光系
    DARK = "dark"      # 暗系
    NORMAL = "normal"  # 一般

class Creature(db.Model):
    """精靈模型"""
    __tablename__ = 'creatures'
    
    id = db.Column(db.Integer, primary_key=True)
    random_id = db.Column(db.String(32), unique=True, nullable=False)  # 隨機生成的唯一 ID
    name = db.Column(db.String(64), nullable=False)
    species = db.Column(db.String(64), nullable=False)  # 精靈種類
    element_type = db.Column(db.Enum(ElementType), nullable=False)
    level = db.Column(db.Integer, default=1)
    experience = db.Column(db.Integer, default=0)
    
    # 精靈屬性 - 現在使用範圍隨機生成
    hp = db.Column(db.Integer, default=100)  # 生命值
    attack = db.Column(db.Integer, default=10)  # 攻擊力
    
    image_url = db.Column(db.String(256))  # 精靈圖片URL
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 捕獲此精靈的玩家 ID 列表 (儲存為逗號分隔的字符串)
    captured_players = db.Column(db.Text, default="")
    
    # 關聯
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    bus_route_id = db.Column(db.Integer, db.ForeignKey('bus_routes.id'), nullable=True)
    arena_id = db.Column(db.Integer, db.ForeignKey('arenas.id'), nullable=True)
      # 關聯查詢
    bus_route = db.relationship('BusRoute', backref='creatures')
    
    def add_player_to_captured(self, player_id):
        """將玩家添加到已捕獲列表中"""
        if not self.captured_players:
            self.captured_players = player_id
        else:
            # 檢查玩家是否已在列表中
            player_list = self.captured_players.split(',')
            if player_id not in player_list:
                player_list.append(player_id)
                self.captured_players = ','.join(player_list)
        return self
    
    def is_captured_by_player(self, player_id):
        """檢查是否已被特定玩家捕獲"""
        if not self.captured_players:
            return False
        player_list = self.captured_players.split(',')
        return player_id in player_list
    
    def get_captured_players(self):
        """獲取已捕獲此精靈的玩家 ID 列表"""
        if not self.captured_players:
            return []
        return self.captured_players.split(',')
    
    def to_dict(self):
        """將精靈數據轉換為字典（用於API）"""
        return {
            'id': self.id,
            'random_id': self.random_id,
            'name': self.name,
            'species': self.species,
            'rate': self.species,
            'rarity': self.species,
            'element_type': self.element_type.value,
            'element': self.element_type.value,
            'type': self.element_type.value,
            'level': self.level,
            'experience': self.experience,
            'attack': self.attack,
            'power': self.attack,
            'hp': self.hp,
            'image_url': self.image_url or get_creature_image_url(self.name),
            'owner_id': self.user_id,
            'bus_route': self.bus_route.name if self.bus_route else None,
            'captured_players': self.get_captured_players()
        }
    
    def __repr__(self):
        return f'<Creature {self.name} ({self.species}/{self.element_type.value})>'
