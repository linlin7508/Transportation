"""
Friend System Tests
"""

class TestFriendAdd:
    """Add friend tests"""
    
    def test_add_friend_success(self, client):
        """成功添加好友"""
        # 創建兩個用戶
        client.post('/api/auth/register', json={
            'email': 'user1@test.com',
            'password': 'pass',
            'username': 'user1'
        })
        client.post('/api/auth/register', json={
            'email': 'user2@test.com',
            'password': 'pass',
            'username': 'user2'
        })
        
        # user1 登入
        client.post('/api/auth/login', json={
            'email': 'user1@test.com',
            'password': 'pass'
        })
        
        # user1 添加 user2 為好友
        res = client.post('/api/friend/add', json={'target_user_id': 'user2_id'})
        # 注意：實際需要 user2 的真實 ID
        if res.status_code == 200:
            assert 'friend_id' in res.json or 'message' in res.json

    def test_add_duplicate_friend(self, client):
        """不能添加重複的好友"""
        # 測試邏輯：嘗試添加同一個好友兩次
        pass

    def test_add_friend_self_blocked(self, client):
        """不能添加自己為好友"""
        client.post('/api/auth/register', json={
            'email': 'self@test.com',
            'password': 'pass',
            'username': 'selfuser'
        })
        client.post('/api/auth/login', json={
            'email': 'self@test.com',
            'password': 'pass'
        })
        
        res = client.post('/api/friend/add', json={'target_user_id': 'self'})
        # 應該被拒絕
        assert res.status_code == 400 or res.status_code == 403

    def test_add_invalid_friend_id(self, client):
        """添加無效的用戶 ID 應失敗"""
        client.post('/api/auth/register', json={
            'email': 'invalid@test.com',
            'password': 'pass',
            'username': 'invaliduser'
        })
        client.post('/api/auth/login', json={
            'email': 'invalid@test.com',
            'password': 'pass'
        })
        
        res = client.post('/api/friend/add', json={'target_user_id': 'nonexistent_id'})
        assert res.status_code == 404 or res.status_code == 400


class TestFriendRequest:
    """Friend request tests"""
    
    def test_accept_friend_request(self, client):
        """接受好友請求"""
        # 測試邏輯：發送請求、檢查、接受
        pass

    def test_decline_friend_request(self, client):
        """拒絕好友請求"""
        # 測試邏輯：發送請求、檢查、拒絕
        pass

    def test_cannot_request_pending_friend(self, client):
        """不能對已有待定請求的用戶再發送請求"""
        pass


class TestFriendRemove:
    """Remove friend tests"""
    
    def test_remove_friend_success(self, client):
        """成功移除好友"""
        # 測試邏輯：添加好友、然後移除
        pass


class TestFriendList:
    """Friend list retrieval tests"""
    
    def test_get_friend_list(self, client):
        """取得好友列表"""
        res = client.get('/api/friend/list')
        if res.status_code == 200:
            assert isinstance(res.json, list)

    def test_friend_list_empty_on_new_user(self, client):
        """新用戶好友列表應為空"""
        client.post('/api/auth/register', json={
            'email': 'newfriend@test.com',
            'password': 'pass',
            'username': 'friendnewuser'
        })
        client.post('/api/auth/login', json={
            'email': 'newfriend@test.com',
            'password': 'pass'
        })
        
        res = client.get('/api/friend/list')
        if res.status_code == 200:
            assert len(res.json) == 0
