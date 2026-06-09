from flask import Flask

def init_routes(app: Flask):
    """初始化所有路由"""
    # Phase 5: v2 Clean REST API Layer
    from app.routes.arena import bp as arena_bp
    from app.routes.creature import bp as creature_bp
    from app.routes.fight import bp as fight_bp
    
    # Register Phase 5 API
    app.register_blueprint(arena_bp)
    app.register_blueprint(creature_bp)
    app.register_blueprint(fight_bp)
    
    return app
