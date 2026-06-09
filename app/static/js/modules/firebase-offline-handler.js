// Firebase 離線處理相容層
//
// 目前地圖資料已改由本機 Flask API 提供；這個模組保留給
// bus-route-map.js 的既有 import，避免缺檔導致整個 ES module 載入失敗。

const firebaseOfflineHandler = {
    isAvailable() {
        return typeof window !== 'undefined' && typeof window.firebase !== 'undefined';
    },

    isOffline() {
        return typeof navigator !== 'undefined' ? !navigator.onLine : false;
    },

    handleError(error, context = 'firebase') {
        console.warn(`${context} offline handler:`, error);
        return null;
    },

    onStatusChange(callback) {
        if (typeof window === 'undefined' || typeof callback !== 'function') {
            return function noop() {};
        }

        const notify = () => callback({ online: navigator.onLine });
        window.addEventListener('online', notify);
        window.addEventListener('offline', notify);

        return function unsubscribe() {
            window.removeEventListener('online', notify);
            window.removeEventListener('offline', notify);
        };
    }
};

export default firebaseOfflineHandler;
