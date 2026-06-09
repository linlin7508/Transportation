import pytest
from app import create_app
from app.extensions import db

@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for the test session."""
    app = create_app("testing")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "postgresql://postgres:postgres@localhost:5433/test_db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SESSION_TYPE": None,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Flask test client that retains cookies (session)."""
    return app.test_client(use_cookies=True)

@pytest.fixture(autouse=True)
def cleanup(app):
    """Rollback DB after each test to keep isolation."""
    yield
    db.session.rollback()
