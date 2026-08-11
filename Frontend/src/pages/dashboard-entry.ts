import type { Role } from '../api/types.js';
import { activeRoles } from '../app/permissions.js';
import { primaryRole } from '../ui/role-experience.js';
import { renderDashboardPage } from './dashboard-v2.js';
import { renderRoleDashboardPage } from './role-dashboard.js';
import type { RoleDashboardKind } from '../api/role-dashboard.js';

const dashboardByPrimaryRole: Partial<Record<Role, RoleDashboardKind>> = {
  organization_admin: 'manager',
  school_manager: 'manager',
  educational_deputy: 'educational',
  student_affairs_deputy: 'studentAffairs',
  counselor: 'counselor',
  guide_teacher: 'guideTeacher',
  teacher: 'teacher',
};

export function dashboardKindForRoles(roles: Role[]): RoleDashboardKind | null {
  if (!roles.length) return null;
  return dashboardByPrimaryRole[primaryRole(roles)] ?? null;
}

/**
 * Role dashboards use their dedicated aggregate read models when the backend
 * supports them. System administration and data operations retain the generic
 * operational dashboard because their cross-organization work has no single
 * role-specific aggregate.
 */
export async function renderDashboardEntryPage(): Promise<HTMLElement> {
  const kind = dashboardKindForRoles(activeRoles());
  return kind ? renderRoleDashboardPage(kind) : renderDashboardPage();
}
