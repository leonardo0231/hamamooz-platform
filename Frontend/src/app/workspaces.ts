import type { Role } from '../api/types.js';
import { policyManagementRoles } from './permissions.js';
import { primaryRole } from '../ui/role-experience.js';

export interface StaffWorkspace {
  id: string;
  href: string;
  label: string;
  icon: string;
  roles?: Role[];
  activePrefixes: string[];
}

export const educationWorkspaceRoles: Role[] = [
  'system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'teacher',
];

export const attendanceWorkspaceRoles: Role[] = [
  'system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'student_affairs_deputy', 'teacher',
];

export const followUpWorkspaceRoles: Role[] = [
  'system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'student_affairs_deputy', 'counselor', 'guide_teacher',
];

export const dataCenterWorkspaceRoles: Role[] = [
  'system_admin', 'organization_admin', 'school_manager', 'operator',
];

export const studentWorkspaceRoles: Role[] = [
  'system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'student_affairs_deputy', 'teacher', 'counselor', 'guide_teacher',
];

/** Policy managers need this workspace even if they cannot manage users. */
export const administrationWorkspaceRoles: Role[] = policyManagementRoles;

export const reportWorkspaceRoles: Role[] = [
  'system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'student_affairs_deputy',
];

export const staffWorkspaces: StaffWorkspace[] = [
  { id: 'home', href: '/', label: 'خانه', icon: 'home', activePrefixes: ['/'] },
  { id: 'students', href: '/students', label: 'دانش‌آموزان', icon: 'users', roles: studentWorkspaceRoles, activePrefixes: ['/students'] },
  {
    id: 'education', href: '/education', label: 'آموزش', icon: 'book', roles: educationWorkspaceRoles,
    activePrefixes: ['/education', '/resources/classes', '/resources/course-offerings', '/resources/assessments', '/resources/scores', '/resources/monthly-evaluations'],
  },
  {
    id: 'attendance', href: '/attendance', label: 'حضور و غیاب', icon: 'calendar', roles: attendanceWorkspaceRoles,
    activePrefixes: ['/attendance', '/alerts', '/resources/attendance-sessions', '/resources/attendance-records', '/resources/parent-notifications'],
  },
  {
    id: 'follow-up', href: '/follow-up', label: 'رشد و پیگیری', icon: 'warning', roles: followUpWorkspaceRoles,
    activePrefixes: ['/follow-up', '/resources/behavior-events', '/resources/activities', '/resources/analytics-risk-signals', '/resources/operational-alerts', '/resources/recommendations', '/resources/guide-', '/resources/counseling-'],
  },
  {
    id: 'reports', href: '/reports', label: 'گزارش‌ها', icon: 'file', roles: reportWorkspaceRoles,
    activePrefixes: ['/reports', '/resources/report-drafts'],
  },
  {
    id: 'data-center', href: '/data-center', label: 'مرکز داده', icon: 'upload', roles: dataCenterWorkspaceRoles,
    activePrefixes: ['/data-center', '/imports', '/manual-entry'],
  },
  {
    id: 'administration', href: '/administration', label: 'مدیریت سامانه', icon: 'settings', roles: administrationWorkspaceRoles,
    activePrefixes: ['/administration', '/settings', '/users', '/roles', '/resources/organizations', '/resources/schools', '/resources/academic-years', '/resources/terms', '/resources/grade-levels', '/resources/subjects', '/resources/grade-subjects', '/resources/assessment-types', '/resources/calculation-policies', '/resources/attendance-policies', '/resources/role-assignments'],
  },
];

/**
 * A person may hold several backend permissions. The staff navigation uses one
 * primary work context instead of the union of every permission family, so the
 * sidebar remains a task map rather than an API-resource inventory.
 */
export function staffNavigationForRoles(roles: Role[]): StaffWorkspace[] {
  if (!roles.length) return staffWorkspaces.filter(workspace => workspace.id === 'home');
  const contextRole = primaryRole(roles);
  return staffWorkspaces.filter(workspace => !workspace.roles || workspace.roles.includes(contextRole));
}

export function isStaffWorkspaceActive(workspace: StaffWorkspace, pathname = location.pathname): boolean {
  return workspace.activePrefixes.some(prefix => prefix === '/' ? pathname === '/' : pathname.startsWith(prefix));
}
