import { app, BrowserWindow, clipboard, ipcMain, session } from 'electron';
import type { IpcMainInvokeEvent } from 'electron';
import started from 'electron-squirrel-startup';
import { ApiClient, HttpError } from './api/client';
import { isObjectId, parseLogQuery } from './api/query';
import type { Result, UserLogin } from './contracts';

declare const MAIN_WINDOW_WEBPACK_ENTRY: string;
declare const MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY: string;

if (started) app.quit();

// Prism is the only development API while panel routes remain proposed.
const client = new ApiClient(
  app.isPackaged ? 'http://127.0.0.1:8000' : 'http://127.0.0.1:4010',
);
let mainWindow: BrowserWindow | null = null;

function onlyMainWindow(event: IpcMainInvokeEvent): void {
  if (
    !mainWindow ||
    event.sender !== mainWindow.webContents ||
    event.senderFrame !== mainWindow.webContents.mainFrame
  )
    throw new Error('Origem IPC inválida.');
}

function handle<T>(
  channel: string,
  action: (value: unknown) => Promise<T> | T,
): void {
  ipcMain.handle(channel, async (event, value: unknown): Promise<Result<T>> => {
    try {
      onlyMainWindow(event);
      return { ok: true, data: await action(value) };
    } catch (error) {
      if (error instanceof HttpError)
        return {
          ok: false,
          error: { message: error.message, status: error.status },
        };
      if (
        error instanceof Error &&
        /inválid|permitido|posterior/.test(error.message)
      )
        return { ok: false, error: { message: error.message } };
      return {
        ok: false,
        error: { message: 'Não foi possível concluir a operação.' },
      };
    }
  });
}

function registerHandlers(): void {
  handle('auth:session', () => client.hasSession());
  handle('auth:logout', () => {
    client.logout();
  });
  handle('auth:login', async (value) => {
    if (typeof value !== 'object' || value === null || Array.isArray(value))
      throw new Error('Credenciais inválidas.');
    const input = value as Record<string, unknown>;
    if (
      Object.keys(input).some((key) => !['email', 'password'].includes(key)) ||
      typeof input.email !== 'string' ||
      typeof input.password !== 'string' ||
      !input.email.includes('@') ||
      !input.password
    )
      throw new Error('Credenciais inválidas.');
    await client.login(input as UserLogin);
  });
  handle('logs:list', (value) => client.listLogs(parseLogQuery(value)));
  handle('logs:get', (value) => {
    if (!isObjectId(value)) throw new Error('ID de log inválido.');
    return client.getLog(value);
  });
  handle('logs:copy-id', (value) => {
    if (!isObjectId(value)) throw new Error('ID de log inválido.');
    clipboard.writeText(value);
  });
  handle('applications:list', () => client.listApplications());
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 760,
    minHeight: 680,
    backgroundColor: '#0b1019',
    title: 'Log Insight',
    webPreferences: {
      preload: MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY,
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  });
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  mainWindow.webContents.on('will-navigate', (event) => event.preventDefault());
  mainWindow.on('closed', () => {
    mainWindow = null;
    client.logout();
  });
  void mainWindow.loadURL(MAIN_WINDOW_WEBPACK_ENTRY);
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler(
    (_contents, _permission, callback) => callback(false),
  );
  registerHandlers();
  createWindow();
});

app.on('window-all-closed', () => app.quit());
