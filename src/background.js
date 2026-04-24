'use strict'
import path from 'path'
import { app, protocol, BrowserWindow, ipcMain } from 'electron'
import {
  createProtocol,
  /* installVueDevtools */
} from 'vue-cli-plugin-electron-builder/lib'

const isDevelopment = process.env.NODE_ENV !== 'production'

// app.commandLine.appendSwitch("no-proxy-server")

// Keep a global reference of the window object, if you don't, the window will
// be closed automatically when the JavaScript object is garbage collected.
let mainWindow

// Change the default app name
if (process.platform === 'win32') {
  app.setAppUserModelId("Gridverse");
}

// Scheme must be registered before the app is ready
protocol.registerSchemesAsPrivileged([{ scheme: 'app', privileges: { secure: true, standard: true } }])

function createWindow() {
  // Create the browser window.
  mainWindow = new BrowserWindow({
    width: 1200, height: 800, icon: path.join(__static, 'grid.ico'),
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  if (process.env.WEBPACK_DEV_SERVER_URL) {
    // Load the url of the dev server if in development mode
    mainWindow.loadURL(process.env.WEBPACK_DEV_SERVER_URL)
    if (!process.env.IS_TEST) mainWindow.webContents.openDevTools()
  } else {
    createProtocol('app')
    // Load the index.html when not in development
    mainWindow.loadURL('app://./index.html')
  }

  mainWindow.on('ready-to-show', function () {
    mainWindow.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// Prepare the Python process (FastAPI server)
let pyProc = null
let pyPort = null

const createPyProc = (casePath, port, server_port) => {
  let script = path.join(__dirname, '../py/server.py')
  pyProc = require('child_process').spawn("python3", [script, "--case", casePath, "--port", server_port])
  pyProc.stdout.on('data', function (chunk) {
    console.log(chunk.toString('utf8'));
  });

  pyProc.stderr.on('data', function (data) {
    console.error(data.toString());
  });
  if (pyProc != null) {
    console.log('FastAPI server started')
  }
}

// Implement the async sleep function
const sleep = (milliseconds) => {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}


const exitPyProc = () => {
  if (pyProc) {
    pyProc.kill();
    pyProc = null;
  }
  pyPort = null
}


// Quit when all windows are closed.
app.on('window-all-closed', () => {
  // On macOS it is common for applications and their menu bar
  // to stay active until the user quits explicitly with Cmd + Q
  if (process.platform !== 'darwin') {
    if (pyProc != null) {
      exitPyProc()
    }
    app.quit()
  }
})

app.on('activate', () => {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (mainWindow === null) {
    createWindow()
  }
})

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', async () => {
  if (isDevelopment && !process.env.IS_TEST) {
    // Install Vue Devtools
    // Devtools extensions are broken in Electron 6.0.0 and greater
    // See https://github.com/nklayman/vue-cli-plugin-electron-builder/issues/378 for more info
    // Electron will not launch with Devtools extensions installed on Windows 10 with dark mode
    // If you are not using Windows 10 dark mode, you may uncomment these lines
    // In addition, if the linked issue is closed, you can upgrade electron and uncomment these lines
    // try {
    //   await installVueDevtools()
    // } catch (e) {
    //   console.error('Vue Devtools failed to install:', e.toString())
    // }

  }
  createWindow()
})

// // Register the channel that the IPCMain will be listening
ipcMain.once('connect', (event, config) => {
  const config_object = JSON.parse(config);
  // Launch the FastAPI server with the case file and port
  createPyProc(config_object.case_path, config_object.port, config_object.server_port || 8000);
})


// Exit cleanly on request from parent process in development mode.
if (isDevelopment) {
  if (process.platform === 'win32') {
    process.on('message', data => {
      if (data === 'graceful-exit') {
        app.quit()
      }
    })
  } else {
    process.on('SIGTERM', () => {
      app.quit()
    })
  }
}
