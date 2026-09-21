const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('doshieAPI', {
  runCommand: (cmd) => ipcRenderer.invoke('run-command', cmd),
  onOutput: (callback) => ipcRenderer.on('command-output', (_event, data) => callback(data))
});
