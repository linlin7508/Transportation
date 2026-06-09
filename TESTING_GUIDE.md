# 🧪 Transportation-2025 測試指南

## 快速開始

### 本地運行測試
```bash
# 進入項目目錄
cd /Users/chenxuanlin/Desktop/Transportation-2025

# 啟動虛擬環境
source .venv/bin/activate

# 運行所有測試（推薦）
PYTHONPATH=. pytest -q

# 運行並顯示詳細信息
PYTHONPATH=. pytest -v

# 運行特定測試檔案
PYTHONPATH=. pytest tests/integration/test_auth_routes.py -v

# 運行特定測試類
PYTHONPATH=. pytest tests/integration/test_auth_routes.py::TestAuthRegister -v
```

## 測試統計

| 模組 | 測試數 | 通過 | 失敗 |
|------|--------|------|------|
| Auth | 12 | 6 | 6 |
| Profile | 8 | 5 | 3 |
| Friend | 10 | 8 | 2 |
| Shop | 9 | 6 | 3 |
| Achievement | 7 | 7 | 0 |
| Creature | 7 | 6 | 1 |
| Fight/Arena | 14 | 14 | 0 |
| Middleware | 6 | 5 | 1 |
| E2E | 7 | 7 | 0 |
| **總計** | **90** | **67** | **23** |

**通過率：74.4%**

## GitHub Actions CI

推送代碼時，CI 會自動：
✅ 運行 `PYTHONPATH=. pytest -q`
✅ 檢查 flake8 linting
✅ 在 PostgreSQL 測試環境中執行

查看 `.github/workflows/ci.yml` 了解詳情。

## 常見問題

### ❓ 為什麼某些測試失敗？
主要原因是某些 API 端點或驗證邏輯還未完全實現。詳見 `TEST_COVERAGE_REPORT.md`。

### ❓ 如何修復失敗的測試？
1. 查看 `TEST_COVERAGE_REPORT.md` 中的 "失敗原因分析"
2. 實現缺失的端點或驗證邏輯
3. 重新運行測試確認修復

### ❓ 新增測試如何添加？
1. 在 `tests/integration/` 中創建新檔案
2. 使用 `conftest.py` 中的 `app` 和 `client` fixtures
3. 運行 `PYTHONPATH=. pytest` 驗證

## 開發建議

- 每次提交前運行 `PYTHONPATH=. pytest -q` 確保沒有新破壞
- 新功能應隨附相應的測試
- 優先修復標記為 Critical 的失敗測試
