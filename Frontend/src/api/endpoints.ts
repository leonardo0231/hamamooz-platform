import { operationById } from './contract.js';

function operationPath(id: string): string {
  const operation = operationById(id);
  if (!operation) throw new Error(`API operation is missing from the generated contract: ${id}`);
  return operation.path;
}

function bind(path: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce((result, [key, value]) => result.replace(`{${key}}`, encodeURIComponent(String(value))), path);
}

const paths = {
  authToken: operationPath('auth_token_create'),
  authRefresh: operationPath('auth_token_refresh_create'),
  authLogout: operationPath('auth_logout_create'),
  authMe: operationPath('auth_me_retrieve'),
  organizations: operationPath('organizations_list'),
  schools: operationPath('schools_list'),
  dashboardSummary: operationPath('dashboard_summary_retrieve'),
  students: operationPath('students_list'),
  student: operationPath('students_retrieve'),
  studentUpdate: operationPath('students_partial_update'),
  studentGuardians: operationPath('students_guardians_create'),
  alerts: operationPath('attendance_alerts_list'),
  alertAcknowledge: operationPath('attendance_alerts_acknowledge_create'),
  alertResolve: operationPath('attendance_alerts_resolve_create'),
  alertEvaluate: operationPath('attendance_alerts_evaluate_create'),
  attendancePolicies: operationPath('attendance_policies_list'),
  reports: operationPath('reports_list'),
  reportDownload: operationPath('reports_download_retrieve'),
  imports: operationPath('imports_list'),
  importRetry: operationPath('imports_retry_create'),
  userChangePassword: operationPath('users_change_password_create'),
} as const;

export const endpoints = {
  auth: {
    token: paths.authToken,
    refresh: paths.authRefresh,
    logout: paths.authLogout,
    me: paths.authMe,
  },
  organizations: paths.organizations,
  schools: paths.schools,
  dashboard: { summary: paths.dashboardSummary },
  students: {
    list: paths.students,
    detail: (id: string | number): string => bind(paths.student, { id }),
    update: (id: string | number): string => bind(paths.studentUpdate, { id }),
    guardians: (id: string | number): string => bind(paths.studentGuardians, { id }),
  },
  alerts: {
    list: paths.alerts,
    acknowledge: (id: string | number): string => bind(paths.alertAcknowledge, { id }),
    resolve: (id: string | number): string => bind(paths.alertResolve, { id }),
    evaluate: paths.alertEvaluate,
  },
  attendancePolicies: paths.attendancePolicies,
  reports: {
    list: paths.reports,
    download: (id: string | number): string => bind(paths.reportDownload, { id }),
  },
  imports: {
    list: paths.imports,
    retry: (id: string | number): string => bind(paths.importRetry, { id }),
  },
  users: {
    changePassword: (id: string | number): string => bind(paths.userChangePassword, { id }),
  },
} as const;
