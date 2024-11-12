const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    startScraping: (data) => ipcRenderer.invoke('start-scraping', data),
    exportData: (data) => ipcRenderer.invoke('export-data', data),
    onScrapingProgress: (callback) => {
        // Remove any existing listeners
        ipcRenderer.removeAllListeners('scraping-progress');
        ipcRenderer.on('scraping-progress', (event, data) => callback(data));
    },
    onScrapingResult: (callback) => {
        // Remove any existing listeners
        ipcRenderer.removeAllListeners('scraping-result');
        ipcRenderer.on('scraping-result', (event, data) => callback(data));
    },
    onScrapingError: (callback) => {
        // Remove any existing listeners
        ipcRenderer.removeAllListeners('scraping-error');
        ipcRenderer.on('scraping-error', (event, data) => callback(data));
    }
});