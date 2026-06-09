from dotenv import load_dotenv
load_dotenv()
from flask import Flask, current_app, session, g
import os
import config as config_module
import logging
import threading
from sqlalchemy import inspect
# 從 extensions 導入
from app.extensions import db, migrate


def fetch_tdx_data():
    """抓取所有 TDX API 資料並儲存到本地"""
    pass


def load_tdx_data_on_startup(app):
    """在應用啟動時預載TDX資料"""
    pass


def create_app(config_name='default', load_tdx=True):
    """工廠函數，用於創建應用實例"""
    app = Flask(__name__)
    app.config.from_object(config_module.config[config_name])
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        app.config.get("SECRET_KEY", "dev-secret-key"),
    )

    # 初始化擴展
    db.init_app(app)
    import app.models as app_models
    migrate.init_app(app, db)

    # Render 上的新 PostgreSQL 不會自動有資料表；目前專案沒有 migrations/
    # 先用 create_all 做 MVP 上線救火，之後再補 Flask-Migrate migration。
    with app.app_context():
        try:
            print("START CREATE TABLES")
            db.create_all()
            inspector = inspect(db.engine)
            print("CREATE TABLES DONE")
            print("TABLES =", inspector.get_table_names())
        except Exception as e:
            print("CREATE TABLES ERROR:", e)

    # Session Authentication Middleware (Phase 7)
    from app.models.user import User

    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        if user_id:
            g.user = User.query.get(user_id)
            if g.user and "user" not in session:
                session["user"] = {
                    "uid": str(g.user.id),
                    "username": g.user.username,
                    "email": g.user.email,
                }
                session.modified = True
        else:
            g.user = None

    # 註冊藍圖
    from app.routes import init_routes
    init_routes(app)

    # 註冊 Auth/Profile (Phase 7)
    from app.routes.auth import auth_bp
    from app.routes.profile import profile_bp
    from app.routes.friend import friend_bp
    from app.routes.friend import friend_api_bp
    from app.routes.game import game_bp
    from app.routes.friend_fight import friend_fight_bp
    from app.routes.shop import shop_bp
    from app.routes.shop import shop_api_bp
    from app.routes.achievement import achievement_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.api_docs import api_docs_bp
    from app.routes.bylin import bylin_bp
    from app.routes.daily_migration import daily_migration_bp
    from app.routes.companion import companion_bp, chat_api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(friend_bp)
    app.register_blueprint(friend_api_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(friend_fight_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(shop_api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(achievement_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_docs_bp)
    app.register_blueprint(bylin_bp)
    app.register_blueprint(daily_migration_bp)
    app.register_blueprint(companion_bp)
    app.register_blueprint(chat_api_bp)

    # 註冊全域錯誤處理 (Phase 6)
    from app.core.error_handler import register_error_handlers
    register_error_handlers(app)

    return app
