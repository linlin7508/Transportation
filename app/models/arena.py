from app.extensions import db
from sqlalchemy.ext.mutable import MutableList
from datetime import datetime

class Arena(db.Model):
    """擂台模型（每個公車站點可以有一個擂台）"""
    __tablename__ = 'arenas'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    
    # 經緯度
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # 道館等級與經過路線 (使用 Mutable JSON - 相容 SQLite 和 PostgreSQL)
    level = db.Column(db.Integer, default=1)
    routes = db.Column(MutableList.as_mutable(db.JSON), default=list)
    challengers = db.Column(MutableList.as_mutable(db.JSON), default=list)
    
    prestige = db.Column(db.Integer, default=0)  # 擂台聲望值，越高越難挑戰
    last_battle = db.Column(db.DateTime, nullable=True)  # 上次對戰時間
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 關聯
    bus_stop_id = db.Column(db.Integer, db.ForeignKey('bus_stops.id'), unique=True, nullable=True)
    master_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)  # 擂台主人
    guardian_id = db.Column(db.Integer, db.ForeignKey('creatures.id'), nullable=True)  # 守護精靈
    
    # 反向關聯
    bus_stop = db.relationship('BusStop', foreign_keys=[bus_stop_id], backref=db.backref('arena', uselist=False))
    guardian = db.relationship('Creature', foreign_keys=[guardian_id])
    battles = db.relationship('Battle', backref='arena', lazy='dynamic')
    
    def to_dict(self):
        """將擂台資料轉換為字典（用於API）"""
        from app.models.creature import Creature
        from app.models.user import User
        guardian = Creature.query.get(self.guardian_id) if self.guardian_id else None
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'level': self.level,
            'routes': self.routes,
            'challengers': self.challengers,
            'bus_stop': self.bus_stop.name if self.bus_stop else None,
            'prestige': self.prestige,
            'master_id': self.master_id,
            'master_name': User.query.get(self.master_id).username if self.master_id else None,
            'guardian': guardian.to_dict() if guardian else None,
            'last_battle': self.last_battle.isoformat() if self.last_battle else None,
            'battle_count': self.battles.count()
        }
    
    def __repr__(self):
        return f'<Arena {self.name}>'


class Battle(db.Model):
    """對戰記錄模型"""
    __tablename__ = 'battles'
    
    id = db.Column(db.Integer, primary_key=True)
    arena_id = db.Column(db.Integer, db.ForeignKey('arenas.id'))
    challenger_id = db.Column(db.String(36), db.ForeignKey('users.id'))  # 挑戰者
    defender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)  # 擂台主
    challenger_creature_id = db.Column(db.Integer, db.ForeignKey('creatures.id'))  # 挑戰者精靈
    defender_creature_id = db.Column(db.Integer, db.ForeignKey('creatures.id'), nullable=True)  # 守護精靈
    winner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)  # 獲勝者
    battle_log = db.Column(db.Text)  # 對戰記錄
    experience_gained = db.Column(db.Integer, default=0)  # 獲得的經驗值
    prestige_change = db.Column(db.Integer, default=0)  # 擂台聲望值變化
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 關聯
    challenger = db.relationship('User', foreign_keys=[challenger_id])
    defender = db.relationship('User', foreign_keys=[defender_id])
    challenger_creature = db.relationship('Creature', foreign_keys=[challenger_creature_id])
    defender_creature = db.relationship('Creature', foreign_keys=[defender_creature_id])
    
    def to_dict(self):
        """將對戰記錄轉換為字典（用於API）"""
        from app.models.user import User
        return {
            'id': self.id,
            'arena_id': self.arena_id,
            'arena_name': self.arena.name if self.arena else None,
            'challenger': self.challenger.username,
            'defender': self.defender.username,
            'challenger_creature': self.challenger_creature.name,
            'defender_creature': self.defender_creature.name,
            'winner': User.query.get(self.winner_id).username if self.winner_id else None,
            'experience_gained': self.experience_gained,
            'prestige_change': self.prestige_change,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Battle {self.id} between {self.challenger.username} and {self.defender.username}>'