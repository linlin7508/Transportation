// 模組：config.js - 共享配置和全局變數

// 定義地圖和圖層變數
let map;
let routeLayer = L.layerGroup();
let stopsLayer = L.layerGroup();
let busesLayer = L.layerGroup();
let userMarker;
let userCircle;

// 精靈圖層
let creaturesLayer = L.layerGroup();

// 道館圖層
let arenaLayer = L.layerGroup();

// 公車位置圖層
let busPositionLayer = L.layerGroup();

// 追蹤已創建的站點/道館，避免重複創建
let uniqueStops = {};

// 路線顏色配置
const routeColors = {
    'cat-right': '#ff9800', // 橙色 - 貓空右線
    'cat-left': '#4caf50', // 綠色 - 貓空左線(動物園)
    'cat-left-zhinan': '#9c27b0', // 紫色 - 貓空左線(指南宮)
    'brown-3': '#8B4513' // 棕色 - 棕3路線
};

// 儲存各路線的座標點
const routeCoordinates = {
    'cat-right': [],
    'cat-left': [],
    'cat-left-zhinan': [],
    'brown-3': []
};

// 精靈生成相關變數
let routeCreatures = []; // 儲存所有路線上的精靈
const MAX_CREATURES_PER_ROUTE = 10; // 每條路線最多精靈數量
const CREATURE_LIFETIME = 5 * 60 * 1000; // 精靈存在時間 (5分鐘，單位毫秒)
const SPAWN_INTERVAL = 60 * 1000; // 生成嘗試間隔 (1分鐘，單位毫秒)
const SPAWN_CHANCE = 0.8; // 生成機率 (80%)

// 各路線的精靈定義
const routeCreatureTypes = {
    // 貓空右線的特有精靈
    'cat-right': [
        { id: 'cr1', name: '右線遊俠', type: '一般', rarity: '普通', power: 45, img: '/static/img/Data/%E6%80%A5%E9%80%9F%E9%B5%9D.png' },
        { id: 'cr2', name: '貓空飛鼠', type: '一般', rarity: '普通', power: 50, img: '/static/img/Data/%E5%BD%88%E5%BD%88%E9%BC%A0.png' },
        { id: 'cr3', name: '纜車守護者', type: '一般', rarity: '稀有', power: 65, img: '/static/img/Data/%E5%85%AB%E6%98%9F%E4%B9%8B%E4%B8%BB.png' }
    ],
    // 貓空左線(動物園)的特有精靈
    'cat-left': [
        { id: 'cl1', name: '猴山之王', type: '一般', rarity: '普通', power: 45, img: '/static/img/Data/%E6%8B%B3%E7%86%8A.png' },
        { id: 'cl2', name: '熊貓使者', type: '一般', rarity: '稀有', power: 70, img: '/static/img/Data/%E6%A3%AE%E9%90%98%E7%86%8A.png' },
        { id: 'cl3', name: '動物園幻影', type: '一般', rarity: '普通', power: 55, img: '/static/img/Data/%E5%BD%B1%E8%B1%B9.png' }
    ],    // 貓空左線(指南宮)的特有精靈
    'cat-left-zhinan': [
        { id: 'cz1', name: '指南星使', type: '一般', rarity: '普通', power: 50, img: '/static/img/Data/%E6%98%9F%E9%B9%BF.png' },
        { id: 'cz2', name: '宮殿守衛', type: '一般', rarity: '稀有', power: 65, img: '/static/img/Data/%E6%9B%9C%E6%98%9F%E7%8D%B8.png' },
        { id: 'cz3', name: '山靈使者', type: '一般', rarity: '普通', power: 55, img: '/static/img/Data/%E6%A3%AE%E9%AD%88%20.png' }
    ],
    // 棕3路線的特有精靈
    'brown-3': [
        { id: 'b31', name: '大地行者', type: 'earth', rarity: '普通', power: 48, img: '/static/img/Data/%E6%A8%B9%E7%94%B2%E7%8D%B8.png' },
        { id: 'b32', name: '岩石守護', type: 'earth', rarity: '稀有', power: 68, img: '/static/img/Data/%E7%88%90%E5%B2%A9%E8%9F%B2.png' },
        { id: 'b33', name: '土靈戰士', type: 'earth', rarity: '普通', power: 52, img: '/static/img/Data/%E6%B2%99%E5%8C%85%E7%8D%B8.png' }
    ]
};

// 導出模組
export {
    map,
    routeLayer,
    stopsLayer,
    busesLayer,
    userMarker,
    userCircle,
    creaturesLayer,
    arenaLayer,
    busPositionLayer,
    uniqueStops,
    routeColors,
    routeCoordinates,
    routeCreatures,
    MAX_CREATURES_PER_ROUTE,
    CREATURE_LIFETIME,
    SPAWN_INTERVAL,
    SPAWN_CHANCE,
    routeCreatureTypes
};
