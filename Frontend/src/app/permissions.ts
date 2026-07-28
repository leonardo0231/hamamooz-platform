import { store } from './store.js';
import type { Role } from '../api/types.js';

export const administrativeRoles: Role[] = ['system_admin', 'organization_admin', 'school_manager'];
export const managementReadRoles: Role[] = [...administrativeRoles, 'educational_deputy'];
export const organizationManagementRoles: Role[] = ['system_admin', 'organization_admin'];
export const policyManagementRoles: Role[] = ['system_admin', 'organization_admin', 'school_manager', 'educational_deputy'];
export const broadEducationRoles: Role[] = ['system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'operator'];
export const teacherWriteRoles: Role[] = [...broadEducationRoles, 'teacher'];
export const curriculumManagementRoles: Role[] = ['system_admin', 'organization_admin', 'educational_deputy'];

export function activeRoles(): Role[] {
  return [...new Set((store.state.user?.role_assignments ?? []).filter(item => item.is_active).map(item => item.role))];
}

export function hasAnyRole(roles?: Role[]): boolean {
  if (!roles?.length) return true;
  const current = activeRoles();
  return current.includes('system_admin') || roles.some(role => current.includes(role));
}

export function hasWriteScope(): boolean {
  return isSystemAdmin() || Boolean(store.state.scope.schoolId || store.state.scope.organizationId);
}

export function isSystemAdmin(): boolean {
  return activeRoles().includes('system_admin');
}

export function roleLabel(role: Role): string {
  const labels: Record<Role, string> = {
    system_admin: 'مدیر کل سامانه',
    organization_admin: 'مدیر مجموعه',
    school_manager: 'مدیر مدرسه',
    educational_deputy: 'معاون آموزشی',
    operator: 'اپراتور',
    teacher: 'دبیر',
  };
  return labels[role];
}
