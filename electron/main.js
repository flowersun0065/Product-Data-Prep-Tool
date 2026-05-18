const { app, BrowserWindow, Menu, dialog, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow = null;
let settingsWindow = null;
let detailWindow = null;
let flaskProcess = null;

// Determine data directory
function getDataDir() {
  const userDataPath = app.getPath('userData');
  return userDataPath;
}

// Start Python Flask backend
function startFlaskBackend() {
  return new Promise((resolve, reject) => {
    const dataDir = getDataDir();
    const venvPython = path.join(dataDir, 'venv', 'bin', 'python3');
    const args = ['run_server.py', '--electron', '--data-dir', dataDir];

    if (!fs.existsSync(venvPython)) {
      if (mainWindow) {
        mainWindow.webContents.send('venv-setup-needed');
      }
      reject(new Error('VENV_NOT_READY'));
      return;
    }

    flaskProcess = spawn(venvPython, args, {
      cwd: path.join(__dirname, '..'),
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });

    let started = false;
    flaskProcess.stdout.on('data', (data) => {
      const line = data.toString();
      console.log('[flask]', line);
      if (line.includes('Running on') && !started) {
        started = true;
        resolve();
      }
    });

    flaskProcess.stderr.on('data', (data) => {
      console.error('[flask-err]', data.toString());
    });

    flaskProcess.on('close', (code) => {
      console.log(`[flask] exited with code ${code}`);
      flaskProcess = null;
      if (!started) reject(new Error(`Flask exited with code ${code}`));
    });

    setTimeout(() => {
      if (!started) reject(new Error('Flask startup timeout (10s)'));
    }, 10000);
  });
}

// Setup Python venv (first launch)
async function setupVenv() {
  const dataDir = getDataDir();
  fs.mkdirSync(path.join(dataDir, 'venv'), { recursive: true });

  return new Promise((resolve, reject) => {
    const proc = spawn('python3', [
      '-m', 'venv', path.join(dataDir, 'venv')
    ], { cwd: path.join(__dirname, '..') });

    proc.on('close', (code) => {
      if (code === 0) {
        const pipBinary = process.platform === 'win32'
          ? path.join(dataDir, 'venv', 'Scripts', 'pip.exe')
          : path.join(dataDir, 'venv', 'bin', 'pip');
        const pip = spawn(pipBinary, [
          'install', '-r', 'requirements.txt'
        ], { cwd: path.join(__dirname, '..') });
        pip.stdout.on('data', (d) => {
          if (mainWindow) {
            mainWindow.webContents.send('venv-setup-progress', d.toString());
          }
        });
        pip.stderr.on('data', (d) => {
          if (mainWindow) {
            mainWindow.webContents.send('venv-setup-progress', d.toString());
          }
        });
        pip.on('close', (pipCode) => {
          if (pipCode === 0) resolve();
          else reject(new Error(`pip install failed with code ${pipCode}`));
        });
      } else {
        reject(new Error(`venv creation failed with code ${code}`));
      }
    });
  });
}

// Build app menu
function buildMenu() {
  const template = [
    {
      label: app.name,
      submenu: [
        { label: '关于', role: 'about' },
        { label: '设置...', accelerator: 'Cmd+,', click: () => openSettings() },
        { type: 'separator' },
        { label: '退出', accelerator: 'Cmd+Q', click: () => app.quit() },
      ],
    },
    {
      label: '文件',
      submenu: [
        {
          label: '导入文件...',
          accelerator: 'Cmd+O',
          click: () => {
            if (mainWindow) mainWindow.webContents.send('menu-open-file');
          },
        },
        { type: 'separator' },
        { label: '导出结果...', accelerator: 'Cmd+Shift+E', click: () => {
          if (mainWindow) mainWindow.webContents.send('menu-export');
        }},
      ],
    },
    {
      label: '编辑',
      submenu: [
        { label: '撤销', accelerator: 'Cmd+Z', role: 'undo' },
        { label: '重做', accelerator: 'Shift+Cmd+Z', role: 'redo' },
        { type: 'separator' },
        { label: '剪切', accelerator: 'Cmd+X', role: 'cut' },
        { label: '拷贝', accelerator: 'Cmd+C', role: 'copy' },
        { label: '粘贴', accelerator: 'Cmd+V', role: 'paste' },
      ],
    },
    {
      label: '窗口',
      submenu: [
        { label: '关闭', accelerator: 'Cmd+W', role: 'close' },
        { label: '缩放', role: 'zoom' },
        { type: 'separator' },
        {
          label: '商品详情新窗口',
          accelerator: 'Cmd+Shift+D',
          click: () => {
            if (mainWindow) mainWindow.webContents.send('open-detail-window');
          },
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// Settings window
function openSettings() {
  if (settingsWindow) {
    settingsWindow.focus();
    return;
  }
  settingsWindow = new BrowserWindow({
    width: 640,
    height: 480,
    title: '设置',
    resizable: false,
    parent: mainWindow,
    modal: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  settingsWindow.loadFile(path.join(__dirname, 'settings.html'));
  settingsWindow.on('closed', () => { settingsWindow = null; });
}

// Detail window (independent review detail)
function openDetailWindow(data) {
  if (detailWindow) {
    detailWindow.close();
  }
  detailWindow = new BrowserWindow({
    width: 400,
    height: 600,
    title: '商品详情',
    parent: mainWindow,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  // Load a simple detail page; data passed via IPC
  detailWindow.loadURL('http://localhost:5001/electron');
  detailWindow.webContents.on('did-finish-load', () => {
    detailWindow.webContents.send('detail-data', data);
  });
  detailWindow.on('closed', () => { detailWindow = null; });
}

// Create main window
async function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 800,
    title: '产品数据清洗工具',
    titleBarStyle: 'hiddenInset',
    vibrancy: 'under-window',
    visualEffectState: 'active',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL('http://localhost:5001/electron');
  mainWindow.on('closed', () => { mainWindow = null; });
}

// IPC handlers
ipcMain.handle('open-file-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [{ name: 'Excel', extensions: ['xlsx', 'xls'] }],
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('get-data-dir', () => getDataDir());
ipcMain.handle('setup-venv', async () => { await setupVenv(); });
ipcMain.handle('flask-restart', async () => {
  if (flaskProcess) { flaskProcess.kill(); flaskProcess = null; }
  await startFlaskBackend();
});

ipcMain.on('open-detail-window', (event, data) => { openDetailWindow(data); });
ipcMain.on('open-settings', () => { openSettings(); });

// App lifecycle
app.whenReady().then(async () => {
  buildMenu();

  try {
    await startFlaskBackend();
  } catch (e) {
    if (e.message === 'VENV_NOT_READY') {
      console.log('Venv not ready, will show setup UI');
    }
  }

  await createMainWindow();
});

app.on('window-all-closed', () => {
  if (flaskProcess) {
    const http = require('http');
    const req = http.request({ hostname: '127.0.0.1', port: 5001, path: '/api/shutdown', method: 'POST' });
    req.on('error', () => {});
    req.end();
    setTimeout(() => {
      if (flaskProcess) flaskProcess.kill();
      app.quit();
    }, 1000);
  } else {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (flaskProcess) flaskProcess.kill();
});
