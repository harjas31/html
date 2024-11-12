const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    mainWindow.loadFile('index.html');
    
    // Optional: Open DevTools for debugging
    // mainWindow.webContents.openDevTools();
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

// Handle scraping requests
ipcMain.handle('start-scraping', async (event, data) => {
    const { type, keywords, numProducts } = data;
    const pythonPath = path.join(__dirname, 'python');
    
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(pythonPath, 'scraper_wrapper.py');
        const args = [
            scriptPath,
            '--keywords', keywords.join(','),
            '--num_products', numProducts?.toString() || '30',
            '--platform', type.includes('amazon') ? 'amazon' : 'flipkart',
            '--type', type.includes('product') ? 'product' : 'rank'
        ];

        console.log('Starting Python process with args:', args);

        const pythonProcess = spawn('python', args);
        let allResults = [];

        pythonProcess.stdout.on('data', (data) => {
            try {
                const lines = data.toString().trim().split('\n');
                for (const line of lines) {
                    if (!line.trim()) continue;
                    
                    const jsonData = JSON.parse(line);
                    console.log('Received data from Python:', jsonData.type);
                    
                    switch(jsonData.type) {
                        case 'progress':
                            mainWindow.webContents.send('scraping-progress', {
                                current: jsonData.current,
                                total: jsonData.total,
                                keyword: jsonData.keyword
                            });
                            break;
                            
                        case 'result':
                            if (jsonData.data) {
                                allResults = allResults.concat(
                                    Array.isArray(jsonData.data) ? jsonData.data : [jsonData.data]
                                );
                                mainWindow.webContents.send('scraping-result', {
                                    result: jsonData.data
                                });
                            }
                            break;
                            
                        case 'complete':
                            console.log('Scraping complete, total results:', allResults.length);
                            resolve(allResults);
                            break;
                            
                        case 'error':
                            console.error('Python error:', jsonData.message);
                            mainWindow.webContents.send('scraping-error', {
                                message: jsonData.message,
                                keyword: jsonData.keyword
                            });
                            break;
                    }
                }
            } catch (e) {
                console.error('Error parsing Python output:', e);
                console.error('Raw output:', data.toString());
            }
        });

        pythonProcess.stderr.on('data', (data) => {
            console.error(`Python Error: ${data}`);
            mainWindow.webContents.send('scraping-error', {
                message: data.toString()
            });
        });

        pythonProcess.on('close', (code) => {
            console.log(`Python process exited with code ${code}`);
            if (code !== 0) {
                reject(`Process exited with code ${code}`);
            }
        });

        pythonProcess.on('error', (error) => {
            console.error('Failed to start Python process:', error);
            reject(error.message);
        });
    });
});

// Handle export requests
ipcMain.handle('export-data', async (event, data) => {
    const saveDialogOptions = {
        filters: [{ name: 'Excel Files', extensions: ['xlsx'] }],
        defaultPath: path.join(app.getPath('documents'), 'scraping_results.xlsx')
    };

    try {
        const { filePath } = await dialog.showSaveDialog(mainWindow, saveDialogOptions);
        if (!filePath) {
            console.log('Export cancelled by user');
            return false;
        }

        console.log('Exporting to:', filePath);

        const pythonPath = path.join(__dirname, 'python', 'export_utils.py');
        
        return new Promise((resolve, reject) => {
            const pythonProcess = spawn('python', [
                pythonPath,
                '--data', JSON.stringify(data.results),
                '--output', filePath,
                '--platform', data.platform
            ]);

            let errorOutput = '';

            pythonProcess.stdout.on('data', (data) => {
                console.log('Export progress:', data.toString());
            });

            pythonProcess.stderr.on('data', (data) => {
                errorOutput += data.toString();
                console.error('Export error:', data.toString());
            });

            pythonProcess.on('close', (code) => {
                console.log(`Export process exited with code ${code}`);
                if (code === 0) {
                    resolve(true);
                } else {
                    reject(`Export failed: ${errorOutput}`);
                }
            });

            pythonProcess.on('error', (error) => {
                console.error('Failed to start export process:', error);
                reject(error.message);
            });
        });

    } catch (error) {
        console.error('Export error:', error);
        throw error;
    }
});