import type { components, operations } from './api/schema';

export type LogRead = components['schemas']['LogRead'];
export type LogPage = components['schemas']['LogPage'];
export type ApplicationList = components['schemas']['ApplicationList'];
export type UserLogin = components['schemas']['UserLogin'];
export type LogQuery = NonNullable<
  operations['listLogs']['parameters']['query']
>;
export type ApiError = { message: string; status?: number };
export type Result<T> = { ok: true; data: T } | { ok: false; error: ApiError };

export interface LogApi {
  login(credentials: UserLogin): Promise<Result<void>>;
  logout(): Promise<Result<void>>;
  session(): Promise<Result<boolean>>;
  listLogs(query: LogQuery): Promise<Result<LogPage>>;
  getLog(id: string): Promise<Result<LogRead>>;
  copyLogId(id: string): Promise<Result<void>>;
  listApplications(): Promise<Result<ApplicationList>>;
}
