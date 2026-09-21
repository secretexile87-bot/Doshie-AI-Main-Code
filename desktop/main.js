const { app, BrowserWindow, Tray, Menu, globalShortcut, nativeImage, shell, session } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

const DOSHIE_URL = 'http://127.0.0.1:5000';
const VOICE_STUDIO_URL = 'http://127.0.0.1:7860';
const ICON_PATH = path.join(__dirname, 'icon.png');

let mainWindow = null;
let splashWindow = null;
let tray = null;
let serverProcess = null;
let isQuitting = false;

// Hardware acceleration and Linux Wayland/X11 optimizations
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('ignore-gpu-blocklist');

function checkServerStatus(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 500);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1200, () => {
      req.destroy();
      resolve(false);
    });
  });
}

function ensureLocalServerRunning() {
  checkServerStatus(DOSHIE_URL).then((isRunning) => {
    if (!isRunning) {
      console.log('[Doshie Desktop] Local web server not detected on port 5000. Launching...');
      const venvPython = '/home/doshie/Doshie/.venv/bin/python';
      const webScript = '/home/doshie/Doshie/Doshie_web.py';
      serverProcess = spawn(venvPython, [webScript], {
        cwd: '/home/doshie/Doshie',
        detached: true,
        stdio: 'ignore'
      });
      serverProcess.unref();
    }
  });
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 380,
    height: 420,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    show: false,
    resizable: false,
    icon: ICON_PATH,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  splashWindow.loadFile(path.join(__dirname, 'splash.html'));
  splashWindow.once('ready-to-show', () => {
    splashWindow.show();
  });
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 800,
    minHeight: 600,
    show: false,
    backgroundColor: '#0f172a',
    title: 'Doshie - Acer Nitro',
    icon: ICON_PATH,
    autoHideMenuBar: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      backgroundThrottling: false
    }
  });

  // Grant media permissions automatically for local server
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const origin = webContents.getURL();
    if (origin.startsWith('http://127.0.0.1') || origin.startsWith('http://localhost')) {
      if (['media', 'microphone', 'camera', 'notifications', 'audioCapture'].includes(permission)) {
        return callback(true);
      }
    }
    callback(false);
  });

  // Handle external links opening in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(DOSHIE_URL) && !url.startsWith('http://localhost:5000') && !url.startsWith('http://127.0.0.1:5000')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(DOSHIE_URL) && !url.startsWith('http://localhost:5000') && !url.startsWith('http://127.0.0.1:5000')) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      return false;
    }
  });

  mainWindow.webContents.on('did-finish-load', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
  });

  // Polling server until reachable, then load
  const loadDoshie = async () => {
    let attempts = 0;
    while (attempts < 30) {
      const alive = await checkServerStatus(DOSHIE_URL);
      if (alive) {
        mainWindow.loadURL(DOSHIE_URL);
        return;
      }
      attempts++;
      await new Promise((r) => setTimeout(r, 800));
    }
    // Fallback load
    mainWindow.loadURL(DOSHIE_URL);
  };

  loadDoshie();
}

function createTray() {
  const icon = nativeImage.createFromPath(ICON_PATH).resize({ width: 22, height: 22 });
  tray = new Tray(icon);
  tray.setToolTip('Doshie - Acer Nitro Local Interface');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open Doshie Interface',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: 'Open Voice Studio (Port 7860)',
      click: () => {
        shell.openExternal(VOICE_STUDIO_URL);
      }
    },
    {
      label: 'Open MySpace Studio (Theme Customizer)',
      click: () => {
        const studioWin = new BrowserWindow({
          width: 1400,
          height: 900,
          title: 'Doshie MySpace Studio',
          backgroundColor: '#090d16',
          icon: ICON_PATH,
          webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
          }
        });
        studioWin.loadFile(path.join(__dirname, 'myspace-studio', 'index.html'));
      }
    },
    { type: 'separator' },
    {
      label: 'Reload App',
      accelerator: 'CmdOrCtrl+R',
      click: () => {
        if (mainWindow) mainWindow.webContents.reload();
      }
    },
    {
      label: 'Toggle Developer Tools',
      accelerator: 'F12',
      click: () => {
        if (mainWindow) mainWindow.webContents.toggleDevTools();
      }
    },
    { type: 'separator' },
    {
      label: 'Restart Doshie Web Server',
      click: () => {
        ensureLocalServerRunning();
        if (mainWindow) mainWindow.loadURL(DOSHIE_URL);
      }
    },
    {
      label: 'Quit Doshie',
      accelerator: 'CmdOrCtrl+Q',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

function setupGlobalShortcuts() {
  // Global hotkey to summon Doshie instantly from anywhere on the Nitro desktop
  globalShortcut.register('CommandOrControl+Alt+D', () => {
    if (mainWindow) {
      if (mainWindow.isVisible() && mainWindow.isFocused()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    ensureLocalServerRunning();
    createSplashWindow();
    createMainWindow();
    createTray();
    setupGlobalShortcuts();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
      } else if (mainWindow) {
        mainWindow.show();
      }
    });
  });

  app.on('will-quit', () => {
    globalShortcut.unregisterAll();
  });

  app.on('before-quit', () => {
    isQuitting = true;
  });
}
