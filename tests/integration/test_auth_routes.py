"""
Authentication Routes Tests
"""
import pytest
from app.models.user import User
from app.models.profile import Profile

class TestAuthRegister:
    """Register endpoint tests"""
    
    def test_register_success(self, client):
        """成功註冊新用戶"""
        res = client.post('/api/auth/register', json={
            'email': 'newuser@test.com',
            'password': 'securepass123',
            'username': 'newuser'
        })
        assert res.status_code == 200
        assert 'user_id' in res.json
        
        # 確認用戶已建立
        user = User.query.filter_by(email='newuser@test.com').first()
        assert user is not None
        assert user.username == 'newuser'

    def test_register_duplicate_email(self, client):
        """不能用重複的 email 註冊"""
        # 第一次註冊
        client.post('/api/auth/register', json={
            'email': 'duplicate@test.com',
            'password': 'pass123',
            'username': 'user1'
        })
        
        # 第二次用同一 email
        res = client.post('/api/auth/register', json={
            'email': 'duplicate@test.com',
            'password': 'pass456',
            'username': 'user2'
        })
        assert res.status_code == 400 or res.status_code == 409

    def test_register_duplicate_username(self, client):
        """不能用重複的 username 註冊"""
        client.post('/api/auth/register', json={
            'email': 'user1@test.com',
            'password': 'pass123',
            'username': 'sameuser'
        })
        
        res = client.post('/api/auth/register', json={
            'email': 'user2@test.com',
            'password': 'pass456',
            'username': 'sameuser'
        })
        assert res.status_code == 400 or res.status_code == 409

    def test_register_missing_email(self, client):
        """缺少 email 應失敗"""
        res = client.post('/api/auth/register', json={
            'password': 'pass123',
            'username': 'testuser'
        })
        assert res.status_code == 400

    def test_register_missing_password(self, client):
        """缺少 password 應失敗"""
        res = client.post('/api/auth/register', json={
            'email': 'test@test.com',
            'username': 'testuser'
        })
        assert res.status_code == 400

    def test_register_missing_username(self, client):
        """缺少 username 應失敗"""
        res = client.post('/api/auth/register', json={
            'email': 'test@test.com',
            'password': 'pass123'
        })
        assert res.status_code == 400

    def test_register_invalid_email(self, client):
        """無效的 email 格式應失敗"""
        res = client.post('/api/auth/register', json={
            'email': 'not-an-email',
            'password': 'pass123',
            'username': 'testuser'
        })
        assert res.status_code == 400


class TestAuthLogin:
    """Login endpoint tests"""
    
    def test_login_success(self, client):
        """成功登入"""
        # 先註冊
        client.post('/api/auth/register', json={
            'email': 'login@test.com',
            'password': 'secret123',
            'username': 'loginuser'
        })
        
        # 登入
        res = client.post('/api/auth/login', json={
            'email': 'login@test.com',
            'password': 'secret123'
        })
        assert res.status_code == 200
        assert res.json.get('message') in ['logged in', 'login success']

    def test_login_wrong_password(self, client):
        """錯誤密碼應登入失敗"""
        client.post('/api/auth/register', json={
            'email': 'wrongpass@test.com',
            'password': 'correctpass',
            'username': 'wrongpassuser'
        })
        
        res = client.post('/api/auth/login', json={
            'email': 'wrongpass@test.com',
            'password': 'wrongpass'
        })
        assert res.status_code == 401 or res.status_code == 400

    def test_login_nonexistent_email(self, client):
        """不存在的 email 應登入失敗"""
        res = client.post('/api/auth/login', json={
            'email': 'nonexistent@test.com',
            'password': 'anypass'
        })
        assert res.status_code == 401 or res.status_code == 400

    def test_login_missing_email(self, client):
        """缺少 email 應失敗"""
        res = client.post('/api/auth/login', json={
            'password': 'pass123'
        })
        assert res.status_code == 400


class TestAuthLogout:
    """Logout endpoint tests"""
    
    def test_logout_success(self, client):
        """成功登出"""
        # 先登入
        client.post('/api/auth/register', json={
            'email': 'logout@test.com',
            'password': 'pass123',
            'username': 'logoutuser'
        })
        client.post('/api/auth/login', json={
            'email': 'logout@test.com',
            'password': 'pass123'
        })
        
        # 登出
        res = client.post('/api/auth/logout')
        assert res.status_code == 200

    def test_logout_without_login(self, client):
        """未登入就登出應失敗或返回 200"""
        res = client.post('/api/auth/logout')
        # 某些實現會返回 401，某些會返回 200
        assert res.status_code in [200, 401]


class TestAuthSession:
    """Session persistence tests"""
    
    def test_session_persists_after_login(self, client):
        """登入後會話應保持"""
        # 註冊並登入
        client.post('/api/auth/register', json={
            'email': 'session@test.com',
            'password': 'pass123',
            'username': 'sessionuser'
        })
        client.post('/api/auth/login', json={
            'email': 'session@test.com',
            'password': 'pass123'
        })
        
        # 訪問受保護的端點（假設有 /api/auth/me）
        res = client.get('/api/auth/me')
        assert res.status_code == 200

    def test_unauthorized_without_session(self, client):
        """未登入不應能訪問受保護資源"""
        res = client.get('/api/auth/me')
        assert res.status_code == 401 or res.status_code == 403


class TestAuthService:
    """Auth service logic tests"""
    
    def test_password_hashing_security(self, app):
        """密碼應被雜湊化而不是明文儲存"""
        with app.app_context():
            user = User(
                email='test@test.com',
                username='testuser',
                password_hash='plain_text_password'
            )
            from app.models.user import User as UserModel
            # 確認密碼不是明文（這需要使用適當的雜湊）
            assert user.password_hash != 'plain_text_password'

    def test_uuid_generated_on_registration(self, app):
        """新用戶應自動生成 UUID"""
        with app.app_context():
            user = User(
                email='uuid@test.com',
                username='uuiduser',
                password_hash='hashed'
            )
            assert user.id is not None

    def test_profile_auto_created(self, client):
        """註冊後應自動建立 Profile"""
        res = client.post('/api/auth/register', json={
            'email': 'profile@test.com',
            'password': 'pass123',
            'username': 'profileuser'
        })
        
        user = User.query.filter_by(email='profile@test.com').first()
        assert user.profile is not None
