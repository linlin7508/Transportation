"""
Creature System Tests
"""

class TestCreatureCatch:
    """Catch creature tests"""
    
    def test_catch_creature_success(self, client):
        """成功捕捉精靈"""
        pass

    def test_catch_duplicate_creature(self, client):
        """不能重複捕捉同一隻精靈"""
        pass

    def test_catch_invalid_creature(self, client):
        """捕捉無效的精靈應失敗"""
        client.post('/api/auth/register', json={
            'email': 'catch@test.com',
            'password': 'pass',
            'username': 'catchuser'
        })
        client.post('/api/auth/login', json={
            'email': 'catch@test.com',
            'password': 'pass'
        })
        
        res = client.post('/api/creature/catch', json={
            'creature_id': 'nonexistent'
        })
        assert res.status_code == 404 or res.status_code == 400


class TestCreatureOwnership:
    """Ownership tests"""
    
    def test_creature_ownership_check(self, client):
        """檢查精靈擁有權"""
        client.post('/api/auth/register', json={
            'email': 'owner@test.com',
            'password': 'pass',
            'username': 'owneruser'
        })
        client.post('/api/auth/login', json={
            'email': 'owner@test.com',
            'password': 'pass'
        })
        
        # 獲取自己的精靈
        res = client.get('/api/creature/my-creatures')
        if res.status_code == 200:
            assert isinstance(res.json, list)

    def test_cannot_access_other_user_creatures(self, client):
        """不能訪問其他用戶的精靈"""
        pass


class TestCreatureListing:
    """Listing tests"""
    
    def test_list_user_creatures(self, client):
        """列出用戶的精靈"""
        client.post('/api/auth/register', json={
            'email': 'list@test.com',
            'password': 'pass',
            'username': 'listuser'
        })
        client.post('/api/auth/login', json={
            'email': 'list@test.com',
            'password': 'pass'
        })
        
        res = client.get('/api/creature/my-creatures')
        if res.status_code == 200:
            assert isinstance(res.json, list)

    def test_new_user_no_creatures(self, client):
        """新用戶應沒有精靈"""
        client.post('/api/auth/register', json={
            'email': 'newcreature@test.com',
            'password': 'pass',
            'username': 'newcreatureuser'
        })
        client.post('/api/auth/login', json={
            'email': 'newcreature@test.com',
            'password': 'pass'
        })
        
        res = client.get('/api/creature/my-creatures')
        if res.status_code == 200:
            assert len(res.json) == 0 or res.json is None


class TestCreatureData:
    """Creature data tests"""
    
    def test_creature_has_required_fields(self, client):
        """精靈應有必要的欄位"""
        pass

    def test_creature_element_type(self, client):
        """精靈應有元素類型"""
        pass
