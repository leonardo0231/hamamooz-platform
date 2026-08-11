import type { Role } from '../api/types.js';

export interface RouteDefinition {
  pattern: RegExp;
  title: string;
  private: boolean;
  roles?: Role[];
  render: (params: Record<string, string>) => Promise<HTMLElement>;
}

export const routeFactories = {
  login: async (): Promise<HTMLElement> => (await import('../pages/login.js')).renderLoginPage(),
  dashboard: async (): Promise<HTMLElement> => (await import('../pages/dashboard-entry.js')).renderDashboardEntryPage(),
  students: async (): Promise<HTMLElement> => (await import('../pages/resource.js')).renderResourcePage('students'),
  student: async (params: Record<string, string>): Promise<HTMLElement> => (await import('../pages/student.js')).renderStudentPage(params.id ?? ''),
  alerts: async (): Promise<HTMLElement> => (await import('../pages/alerts.js')).renderAlertsPage(),
  attendance: async (): Promise<HTMLElement> => (await import('../pages/attendance.js')).renderAttendancePage(),
  reports: async (): Promise<HTMLElement> => (await import('../pages/reports.js')).renderReportsPage(),
  portal: async (): Promise<HTMLElement> => (await import('../pages/portal.js')).renderPortalPage(),
  imports: async (): Promise<HTMLElement> => (await import('../pages/imports-simple.js')).renderImportsPage(),
  manualEntry: async (): Promise<HTMLElement> => (await import('../pages/manual-entry.js')).renderManualEntryPage(),
  users: async (): Promise<HTMLElement> => (await import('../pages/resource.js')).renderResourcePage('users'),
  roles: async (): Promise<HTMLElement> => (await import('../pages/resource.js')).renderResourcePage('role-assignments'),
  profile: async (): Promise<HTMLElement> => (await import('../pages/profile.js')).renderProfilePage(),
  settings: async (): Promise<HTMLElement> => (await import('../pages/settings.js')).renderSettingsPage(),
  resource: async (params: Record<string, string>): Promise<HTMLElement> => (await import('../pages/resource.js')).renderResourcePage(params.tag ?? ''),
  forbidden: async (): Promise<HTMLElement> => (await import('../pages/errors.js')).renderForbiddenPage(),
  notFound: async (): Promise<HTMLElement> => (await import('../pages/errors.js')).renderNotFoundPage(),
};
