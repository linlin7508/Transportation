// 藥水詳情頁面的 JavaScript

// 藥水數據
const potionData = [
  {
    name: "普通藥水",
    key: "normal",
    img: "/static/img/mybag/potion-normal.png",
    rarity: "common",
    description: "普通的捕捉藥水，輕微提升捕捉能力",
    bonus: "捕捉率 1.13 倍",
    dateAcquired: "2024-05-15",
    usageCount: 12,
    story: "這是旅行商人最常販售的藥水，由常見的草藥調配而成。雖然效果溫和，但對新手冒險者來說非常實用。"
  },
  {
    name: "進階藥水",
    key: "advanced",
    img: "/static/img/mybag/potion-advanced.png",
    rarity: "rare",
    description: "進階捕捉藥水，顯著提升捕捉能力",
    bonus: "捕捉率 1.25 倍",
    dateAcquired: "2024-05-28",
    usageCount: 5,
    story: "由宮廷煉金術師精心調配的藥水，添加了稀有的月光花精華，在月圓之夜製作效果最佳。"
  },
  {
    name: "高級藥水",
    key: "premium",
    img: "/static/img/mybag/potion-high.png",
    rarity: "legendary",
    description: "傳說中的捕捉藥水，大幅提升捕捉能力",
    bonus: "捕捉率 1.50 倍",
    dateAcquired: "2024-06-08",
    usageCount: 2,
    story: "傳說中由龍族賢者親自調配的神秘藥水，融合了星辰之露和鳳凰之淚，擁有不可思議的神奇力量。"
  }
];

// 當文檔加載完成時執行
document.addEventListener('DOMContentLoaded', function() {
  console.log('🧪 初始化藥水詳情頁面...');
  
  // 強制確保主題設置
  const savedTheme = localStorage.getItem('user-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  console.log(`強制設置主題: ${savedTheme}`);
  
  // 初始化主題支持
  initThemeSupport();
  
  // 隱藏CSS測試元素
  const cssTest = document.getElementById('css-test');
  if (cssTest) {
    cssTest.style.display = 'none';
    console.log('CSS已正確載入');
  }
  
  // 設置載入動畫
  document.body.classList.add('is-loading');
  
  // 延遲後隱藏載入動畫
  setTimeout(() => {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
      loadingOverlay.style.opacity = '0';
      loadingOverlay.style.visibility = 'hidden';
      document.body.classList.remove('is-loading');
    }
  }, 1500);
  
  // 載入藥水數據
  loadPotions();
  
  // 更新統計數據
  updateSummary();
  
  // 初始化滾動按鈕
  initScrollButton();
  
  // 初始化使用按鈕事件
  initUseButtons();
  
  // 初始化主題管理功能
  initThemeSupport();
});

// 載入藥水列表
async function loadPotions() {
  const grid = document.getElementById('potion-grid');
  if (!grid) return;
  
  try {
    // 從API獲取藥水數據
    const response = await fetch('/bylin/api/potion-data');
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message);
    }
    
    // 清空現有內容
    grid.innerHTML = '';
    
    const apiPotions = Array.isArray(data.potions)
      ? data.potions
      : Object.entries(data.potions || {}).map(([key, value]) => ({
          key,
          count: typeof value === 'number' ? value : (value?.count || 0)
        }));

    // 合併API數據與靜態數據
    const combinedData = potionData.map(staticItem => {
      const apiItem = apiPotions.find(api => api.key === staticItem.key);
      return {
        ...staticItem,
        quantity: apiItem ? apiItem.count : 0
      };
    });
    
    combinedData.forEach((item, index) => {
      const card = createItemCard(item, index);
      grid.appendChild(card);
    });
    
    // 應用主題到新內容
    grid.querySelectorAll('.item-detail-card').forEach(card => {
      applyThemeToNewContent(card);
    });
    
    console.log('✅ 藥水數據載入完成:', combinedData);
    
  } catch (error) {
    console.error('❌ 載入藥水數據失敗:', error);
    // 顯示錯誤消息
    grid.innerHTML = `
      <div class="error-message" style="
        grid-column: 1 / -1;
        text-align: center;
        padding: 40px;
        background: var(--card-bg);
        border-radius: var(--border-radius);
        border: 1px solid var(--border-color);
        color: var(--details-text-color);
      ">
        <i class="fas fa-exclamation-triangle" style="font-size: 2rem; color: #ff6b6b; margin-bottom: 10px;"></i>
        <h3>載入失敗</h3>
        <p>無法從伺服器獲取藥水數據：${error.message}</p>
        <button onclick="loadPotions()" style="
          margin-top: 10px;
          padding: 8px 16px;
          background: var(--accent-color);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
        ">重新載入</button>
      </div>
    `;
  }
}

// 創建道具卡片
function createItemCard(item, index) {
  const card = document.createElement('div');
  card.className = 'item-detail-card';
  card.setAttribute('data-rarity', item.rarity); // 添加稀有度屬性
  
  const rarityClass = `rarity-${item.rarity}`;
  const rarityText = {
    common: '普通',
    rare: '稀有',
    legendary: '傳說'
  };
  
  card.innerHTML = `
    <div class="item-image-section" style="background-image: url('${item.img}')">
      <div class="item-rarity ${rarityClass}">
        ${rarityText[item.rarity]}
      </div>
      <div class="item-image-overlay">
        <h3 class="item-name">${item.name}</h3>
      </div>
    </div>
    
    <div class="item-content">
      <div class="item-function">
        <h4><i class="fas fa-magic"></i> 功能效果</h4>
        <p>${item.bonus}</p>
      </div>
      
      <div class="item-story">
        <h4><i class="fas fa-book"></i> 道具故事</h4>
        <p>${item.story}</p>
      </div>
        <div class="item-quantity">
        <span class="quantity-label">剩餘數量</span>
        <span class="quantity-value">
          <i class="fas fa-box"></i>
          ${item.quantity || 0} 瓶
        </span>
      </div>
      
      <div class="item-actions">
        <button class="use-potion-btn" data-item-key="${item.key}" ${(item.quantity || 0) <= 0 ? 'disabled' : ''}>
          <i class="fas fa-magic"></i> ${(item.quantity || 0) <= 0 ? '已用完' : '使用藥水'}
        </button>
      </div>
    </div>
  `;
    // 添加動畫延遲
  card.style.animationDelay = `${index * 0.1}s`;
  card.classList.add('fade-in');
  
  // 確保新內容應用主題
  applyThemeToNewContent(card);
  
  return card;
}

// 確保動態內容應用主題
function applyThemeToNewContent(element) {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  if (currentTheme === 'light') {
    // 為新建立的元素強制應用淺色主題樣式
    element.style.color = 'var(--details-text-color)';
    
    // 遞迴處理所有子元素
    const allElements = element.querySelectorAll('*');
    allElements.forEach(el => {
      if (!el.classList.contains('use-potion-btn') && 
          !el.classList.contains('floating-action-btn') &&
          !el.classList.contains('item-rarity')) {
        el.style.color = 'var(--details-text-color)';
      }
    });
    
    // 處理圖標
    const icons = element.querySelectorAll('i, .fa, .fas');
    icons.forEach(icon => {
      if (!icon.closest('.use-potion-btn') && 
          !icon.closest('.floating-action-btn') &&
          !icon.closest('.item-rarity')) {
        icon.style.color = 'var(--accent-color)';
      }
    });
  }
}

// 初始化使用按鈕事件
function initUseButtons() {  // 使用事件委派處理動態生成的按鈕
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('use-potion-btn') || e.target.closest('.use-potion-btn')) {
      const btn = e.target.classList.contains('use-potion-btn') ? e.target : e.target.closest('.use-potion-btn');
      const itemKey = btn.getAttribute('data-item-key');
      
      if (btn.disabled) {
        showNotification('此藥水已用完！', 'warning');
        return;
      }
      
      usePotionItem(itemKey, btn);
    }
  });
}

// 使用藥水
async function usePotionItem(itemKey, button) {
  if (!itemKey) {
    showNotification('道具資訊錯誤', 'warning');
    return;
  }
  
  // 禁用按鈕防止重複點擊
  button.disabled = true;
  const originalText = button.innerHTML;
  button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 使用中...';
  
  try {
    const response = await fetch('/bylin/use-item', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        type: 'potion',
        key: itemKey
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showNotification(`成功使用 ${getPotionName(itemKey)}！`, 'success');
      // 重新載入數據以更新數量
      await loadPotions();
    } else {
      throw new Error(data.message || '使用失敗');
    }
    
  } catch (error) {
    console.error('使用藥水失敗:', error);
    showNotification(`使用失敗: ${error.message}`, 'warning');
    
    // 恢復按鈕狀態
    button.disabled = false;
    button.innerHTML = originalText;
  }
}

// 獲取藥水名稱
function getPotionName(key) {
  const names = {
    'normal': '普通藥水',
    'advanced': '進階藥水',
    'premium': '高級藥水'
  };
  return names[key] || '未知藥水';
  
  // 如果用完了，禁用按鈕
  if (item.usageCount <= 0) {
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-times"></i> 已用完';
    button.style.opacity = '0.5';
    button.style.cursor = 'not-allowed';
  }
  
  // 更新統計
  updateSummary();
  
  // 顯示通知
  showNotification(`已使用 ${item.name}！`, 'success');
  
  console.log(`🧪 使用藥水: ${item.name}，剩餘 ${item.usageCount} 個`);
}

// 更新統計摘要
function updateSummary() {
  const totalElement = document.getElementById('total-potions');
  if (totalElement) {
    const totalCount = potionData.reduce((sum, item) => sum + item.usageCount, 0);
    totalElement.textContent = totalCount;
  }
}

// 初始化滾動按鈕
function initScrollButton() {
  const scrollTopBtn = document.getElementById('scroll-top-btn');
  if (!scrollTopBtn) return;
  
  // 監聽滾動事件
  window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
      scrollTopBtn.classList.add('visible');
    } else {
      scrollTopBtn.classList.remove('visible');
    }
  });
  
  // 點擊事件
  scrollTopBtn.addEventListener('click', () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
}

// 顯示通知
function showNotification(message, type = 'info') {
  // 檢測當前主題
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const isLightTheme = currentTheme === 'light';
  
  const colors = {
    success: isLightTheme ? 'linear-gradient(45deg, #4caf50, #8bc34a)' : 'linear-gradient(45deg, #4caf50, #8bc34a)',
    warning: isLightTheme ? 'linear-gradient(45deg, #ff9800, #ffc107)' : 'linear-gradient(45deg, #ff9800, #ffc107)',
    info: isLightTheme ? 'linear-gradient(45deg, #2196f3, #03a9f4)' : 'linear-gradient(45deg, #2196f3, #03a9f4)'
  };
  
  const textColor = isLightTheme ? 'white' : 'white';
  const shadowColor = isLightTheme ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.3)';
  
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  
  notification.style.cssText = `
    position: fixed;
    top: 30px;
    right: 30px;
    background: ${colors[type] || colors.info};
    color: ${textColor};
    padding: 15px 25px;
    border-radius: 25px;
    box-shadow: 0 5px 15px ${shadowColor};
    z-index: 10000;
    font-weight: 600;
    transform: translateX(400px);
    transition: transform 0.3s ease;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.transform = 'translateX(0)';
  }, 100);
  
  setTimeout(() => {
    notification.style.transform = 'translateX(400px)';
    setTimeout(() => {
      if (notification.parentNode) {
        notification.remove();
      }
    }, 300);
  }, 3000);
}

// 主題管理功能
function initThemeSupport() {
  // 檢查並應用保存的主題設置
  const savedTheme = localStorage.getItem('user-theme');
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  }
  
  // 監聽主題變化事件（由base.html的主題切換按鈕觸發）
  document.addEventListener('themeChanged', function(e) {
    document.documentElement.setAttribute('data-theme', e.detail.theme);
  });
  
  // 監聽localStorage變化（當其他頁面切換主題時）
  window.addEventListener('storage', function(e) {
    if (e.key === 'user-theme') {
      document.documentElement.setAttribute('data-theme', e.newValue);
    }
  });
}

// 添加淡入動畫和按鈕樣式
const style = document.createElement('style');
style.textContent = `
  .fade-in {
    opacity: 0;
    transform: translateY(20px);
    animation: fadeInUp 0.6s ease forwards;
  }
  
  @keyframes fadeInUp {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .item-actions {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid var(--border-color);
  }
    .use-potion-btn {
    width: 100%;
    background: var(--primary-gradient);
    border: none;
    border-radius: 25px;
    padding: 10px 20px;
    color: white !important;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  
  .use-potion-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px var(--shadow-color);
    filter: brightness(1.1);
  }
  
  .use-potion-btn:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    transform: none !important;
  }
`;
document.head.appendChild(style);
