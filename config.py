import uuid
import os

class DefaultConfig(object):
    """Default configuration for production/development."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/transportation'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem'
    TESTING = False
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(DefaultConfig):
    """Development-specific configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(object):
    """Configuration used by pytest for unit tests.
    Uses SQLite in-memory DB for fast testing without external dependencies.
    """
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = None
    TESTING = True
    WTF_CSRF_ENABLED = False


# Configuration map - no circular import
config = {
    'default': DefaultConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig,
}
