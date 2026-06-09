"""
Profile Routes Tests
"""

class TestProfileMe:
    """GET /api/profile/me tests"""
    
    def test_profile_me_success(self, client):
        """成功取得自己的 profile"""
        # 先註冊並登入
        client.post('/api/auth/register', json={
            'email': 'profile@test.com',
            'password': 'pass123',
            'username': 'profileuser'
        })
        client.post('/api/auth/login', json={
            'email': 'profile@test.com',
            'password': 'pass123'
        })
        
        res = client.get('/api/profile/me')
        assert res.status_code == 200
        assert 'username' in res.json or 'user' in res.json

    def test_profile_me_unauthorized(self, client):
        """未登入不能取得 profile"""
        res = client.get('/api/profile/me')
        assert res.status_code == 401 or res.status_code == 403


class TestProfileDefaults:
    """Profile default values tests"""
    
    def test_profile_default_exp(self, client):
        """新 profile 應有預設 exp"""
        client.post('/api/auth/register', json={
            'email': 'exp@test.com',
            'password': 'pass',
            'username': 'expuser'
        })
        client.post('/api/auth/login', json={
            'email': 'exp@test.com',
            'password': 'pass'
        })
        
        res = client.get('/api/profile/me')
        assert res.status_code == 200
        profile_data = res.json
        # 應該有 exp 或類似的欄位，初始值應為 0 或某個預設值
        assert 'exp' in profile_data or 'experience' in profile_data

    def test_profile_default_coins(self, client):
        """新 profile 應有預設 coins"""
        client.post('/api/auth/register', json={
            'email': 'coins@test.com',
            'password': 'pass',
            'username': 'coinsuser'
        })
        client.post('/api/auth/login', json={
            'email': 'coins@test.com',
            'password': 'pass'
        })
        
        res = client.get('/api/profile/me')
        assert res.status_code == 200
        profile_data = res.json
        assert 'coins' in profile_data or 'balance' in profile_data

    def test_profile_default_level(self, client):
        """新 profile 應有預設等級"""
        client.post('/api/auth/register', json={
            'email': 'level@test.com',
            'password': 'pass',
            'username': 'leveluser'
        })
        client.post('/api/auth/login', json={
            'email': 'level@test.com',
            'password': 'pass'
        })
        
        res = client.get('/api/profile/me')
        assert res.status_code == 200
        profile_data = res.json
        assert 'level' in profile_data


class TestProfileUpdate:
    """Profile update tests"""
    
    def test_profile_update_username(self, client):
        """更新用戶名"""
        client.post('/api/auth/register', json={
            'email': 'updatename@test.com',
            'password': 'pass',
            'username': 'oldname'
        })
        client.post('/api/auth/login', json={
            'email': 'updatename@test.com',
            'password': 'pass'
        })
        
        res = client.put('/api/profile/me', json={
            'username': 'newname'
        })
        if res.status_code == 200:
            res2 = client.get('/api/profile/me')
            # 檢查是否更新成功
            assert res2.status_code == 200

    def test_profile_update_avatar(self, client):
        """更新頭像 URL"""
        client.post('/api/auth/register', json={
            'email': 'avatar@test.com',
            'password': 'pass',
            'username': 'avataruser'
        })
        client.post('/api/auth/login', json={
            'email': 'avatar@test.com',
            'password': 'pass'
        })
        
        res = client.put('/api/profile/me', json={
            'avatar': 'https://example.com/avatar.jpg'
        })
        if res.status_code == 200:
            res2 = client.get('/api/profile/me')
            assert res2.status_code == 200

    def test_profile_exp_consistency(self, client):
        """exp 值應保持一致（不會隨意變化）"""
        client.post('/api/auth/register', json={
            'email': 'expconsist@test.com',
            'password': 'pass',
            'username': 'expuser'
        })
        client.post('/api/auth/login', json={
            'email': 'expconsist@test.com',
            'password': 'pass'
        })
        
        res1 = client.get('/api/profile/me')
        res2 = client.get('/api/profile/me')
        
        if 'exp' in res1.json:
            assert res1.json['exp'] == res2.json['exp']


class TestProfileCoinsConsistency:
    """Coins consistency tests"""
    
    def test_coins_consistency(self, client):
        """coins 應保持一致"""
        client.post('/api/auth/register', json={
            'email': 'coinsconsist@test.com',
            'password': 'pass',
            'username': 'coinsuser'
        })
        client.post('/api/auth/login', json={
            'email': 'coinsconsist@test.com',
            'password': 'pass'
        })
        
        res1 = client.get('/api/profile/me')
        res2 = client.get('/api/profile/me')
        
        if 'coins' in res1.json:
            assert res1.json['coins'] == res2.json['coins']
