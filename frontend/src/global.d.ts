import type { LogApi } from './contracts';

declare global {
  interface Window {
    logApi: LogApi;
  }
}

export {};
