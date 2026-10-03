import { contextBridge, ipcRenderer } from 'electron';
import type { LogApi } from './contracts';

const api: LogApi = {
  apiTarget: () => ipcRenderer.invoke('app:api-target'),
  login: (credentials) => ipcRenderer.invoke('auth:login', credentials),
  logout: () => ipcRenderer.invoke('auth:logout'),
  session: () => ipcRenderer.invoke('auth:session'),
  listLogs: (query) => ipcRenderer.invoke('logs:list', query),
  getLog: (id) => ipcRenderer.invoke('logs:get', id),
  copyLogId: (id) => ipcRenderer.invoke('logs:copy-id', id),
  listApplications: () => ipcRenderer.invoke('applications:list'),
};

contextBridge.exposeInMainWorld('logApi', api);
