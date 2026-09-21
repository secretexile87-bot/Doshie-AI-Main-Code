const { app, BrowserWindow, Menu, nativeImage, shell, ipcMain } = require('electron');
const path = require('path');
const { exec } = require('child_process');

let mainWindow = null;
const ICON_PATH = path.join(__dirname, 'icon.png');

app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('ignore-gpu-blocklist');

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 650,
    title: 'Doshie MySpace Studio - Linux Edition',
    backgroundColor: '#090d16',
    icon: ICON_PATH,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// IPC command executor
ipcMain.handle('run-command', async (_event, cmd) => {
  return new Promise((resolve) => {
    const fullCmd = cmd.startsWith('doshie') ? cmd : `/home/doshie/.local/bin/doshie ${cmd}`;
    exec(fullCmd, { cwd: '/home/doshie/Doshie' }, (error, stdout, stderr) => {
      resolve({
        success: !error,
        output: stdout || stderr || (error ? error.message : '')
      });
    });
  });
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
