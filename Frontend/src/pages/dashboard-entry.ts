import type { Role } from '../api/types.js';
import { activeRoles } from '../app/permissions.js';
import { renderDashboardPage } from './dashboard-v2.js';
import { renderRoleDashboardPage } from './role-dashboard.js';
import type { RoleDashboardKind } from '../api/role-dashboard.js';

const directDashboardRoles: Array<[Role, RoleDashboardKind]> = [
  ['counselor', 'counselor'],
  ['guide_teacher', 'guideTeacher'],
  ['student_affairs_deputy', 'studentAffairs'],
];

/**
 * Confidential and cohort-limited roles use their dedicated read models.
 * Existing manager, educational, and teacher dashboards retain the richer
 * established dashboard while their additive API endpoints remain available
 * to clients and integrations.
 */
export async function renderDashboardEntryPage(): Promise<HTMLElement> {
  const roles = activeRoles();
  const direct = directDashboardRoles.find(([role]) => roles.includes(role));
  return direct ? renderRoleDashboardPage(direct[1]) : renderDashboardPage();
}
