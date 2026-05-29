const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // File dialog
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),

  // Data directory
  getDataDir: () => ipcRenderer.invoke('get-data-dir'),

  // Venv setup
  setupVenv: () => ipcRenderer.invoke('setup-venv'),
  onVenvSetupNeeded: (callback) => ipcRenderer.on('venv-setup-needed', callback),
  onVenvSetupProgress: (callback) => ipcRenderer.on('venv-setup-progress', (event, data) => callback(data)),

  // Menu events
  onMenuOpenFile: (callback) => ipcRenderer.on('menu-open-file', callback),
  onMenuExport: (callback) => ipcRenderer.on('menu-export', callback),
  onOpenDetailWindow: (callback) => ipcRenderer.on('open-detail-window', callback),

  // Window controls
  openSettings: () => ipcRenderer.send('open-settings'),
  openDetailWindow: (data) => ipcRenderer.send('open-detail-window', data),
});
