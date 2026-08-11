import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = relative => readFile(new URL(relative, import.meta.url), 'utf8');

test('staff navigation is an eight-workspace task map, not a resource list', async () => {
  const [workspaces, shell] = await Promise.all([
    source('../src/app/workspaces.ts'),
    source('../src/components/shell.ts'),
  ]);
  const navigation = workspaces.slice(workspaces.indexOf('export const staffWorkspaces'), workspaces.indexOf('export function staffNavigationForRoles'));
  const expectedRoutes = ['/', '/students', '/education', '/attendance', '/follow-up', '/reports', '/data-center', '/administration'];
  for (const route of expectedRoutes) assert.match(navigation, new RegExp(`href: '${route.replaceAll('/', '\\/')}'`));
  assert.equal((navigation.match(/href:/g) ?? []).length, 8);
  assert.doesNotMatch(navigation, /href: '\/resources\//);
  assert.doesNotMatch(navigation, /href: '\/portal'/);
  assert.match(shell, /staffNavigationForRoles\(roles\)/);
  assert.doesNotMatch(shell, /label: 'پورتال خانواده و دانش‌آموز'/);
});

test('workspace visibility and role dashboards use a focused primary role', async () => {
  const [workspaces, dashboard] = await Promise.all([
    source('../src/app/workspaces.ts'),
    source('../src/pages/dashboard-entry.ts'),
  ]);
  assert.match(workspaces, /primaryRole\(roles\)/);
  assert.match(workspaces, /educationWorkspaceRoles[\s\S]*?'teacher'/);
  assert.match(workspaces, /dataCenterWorkspaceRoles[\s\S]*?'operator'/);
  assert.match(workspaces, /administrationWorkspaceRoles: Role\[\] = policyManagementRoles/);
  assert.match(dashboard, /organization_admin: 'manager'/);
  assert.match(dashboard, /school_manager: 'manager'/);
  assert.match(dashboard, /educational_deputy: 'educational'/);
  assert.match(dashboard, /teacher: 'teacher'/);
  assert.match(dashboard, /dashboardKindForRoles/);
});

test('workspaces preserve legacy routes while keeping portal and attendance in the right shells', async () => {
  const [router, routes, attendance, portalShell, manualEntry, settings] = await Promise.all([
    source('../src/app/router.ts'),
    source('../src/app/routes.ts'),
    source('../src/pages/attendance.ts'),
    source('../src/components/portal-shell.ts'),
    source('../src/pages/manual-entry.ts'),
    source('../src/pages/settings.ts'),
  ]);
  for (const route of ['/education', '/follow-up', '/data-center', '/administration', '/settings', '/manual-entry']) {
    assert.match(router, new RegExp(route.replaceAll('/', '\\/')));
  }
  assert.match(routes, /shell\?: RouteShell/);
  assert.match(router, /shell: 'portal'/);
  assert.match(router, /createPortalShell/);
  assert.match(portalShell, /portal-shell__main', id: 'page-content'/);
  assert.doesNotMatch(portalShell, /scope-select|apiRequest\(/);
  assert.match(attendance, /\/attendance\/records/);
  assert.match(attendance, /\/attendance\/alerts/);
  assert.doesNotMatch(attendance, /attendance-policies/);
  assert.match(manualEntry, /manual-entry-advanced/);
  assert.match(manualEntry, /requestedTask/);
  assert.match(settings, /roles: Role\[\]/);
  assert.match(settings, /ساختار مدرسه/);
  assert.match(settings, /کاربران و دسترسی/);
});

test('follow-up exposes every live workflow and preserves confidential counseling boundaries', async () => {
  const [followUp, workspace, permissions, resource, dashboards, roleExperience] = await Promise.all([
    source('../src/pages/follow-up.ts'),
    source('../src/pages/workspace.ts'),
    source('../src/app/permissions.ts'),
    source('../src/pages/resource.ts'),
    source('../src/api/role-dashboard.ts'),
    source('../src/ui/role-experience.ts'),
  ]);
  for (const route of [
    '/resources/operational-alerts',
    '/resources/behavior-events',
    '/resources/activities',
    '/resources/analytics-risk-signals',
    '/resources/recommendations',
    '/resources/my-guide-recommendations',
    '/resources/my-counselor-recommendations',
  ]) assert.match(followUp, new RegExp(route.replaceAll('/', '\\/')));
  assert.match(followUp, /id: 'operational-alerts'/);
  assert.match(dashboards, /follow-up\?view=operational-alerts/);
  assert.match(roleExperience, /follow-up\?view=operational-alerts/);
  assert.match(workspace, /exactRoles/);
  assert.match(permissions, /export function hasExactRole/);
  assert.match(resource, /exactReadRoles: counselingRoles/);
});

test('policy managers can reach administration while legacy data entry remains role-gated', async () => {
  const [router, workspaces] = await Promise.all([
    source('../src/app/router.ts'),
    source('../src/app/workspaces.ts'),
  ]);
  assert.match(workspaces, /administrationWorkspaceRoles: Role\[\] = policyManagementRoles/);
  assert.ok(router.includes("pattern: /^\\/administration\\/?$/, title: 'مدیریت سامانه', private: true, roles: administrationWorkspaceRoles"));
  assert.ok(router.includes("pattern: /^\\/manual-entry\\/?$/, title: 'ثبت و ویرایش دستی', private: true, roles: teacherWriteRoles"));
});

test('Student 360 keeps the follow-up sections localized and keyboard-reachable', async () => {
  const [student, presentation] = await Promise.all([
    source('../src/pages/student.ts'),
    source('../src/ui/presentation.ts'),
  ]);
  for (const phrase of ['Behavior events', 'Activities and achievements', 'Risk signals', 'Recommendations', 'No active risk signal']) {
    assert.doesNotMatch(student, new RegExp(`text: '${phrase}'|emptySection\\('${phrase}`));
  }
  assert.match(student, /labelForValue\(event\.polarity\)/);
  assert.match(student, /aria-label': 'جدول رویدادهای رفتاری'/);
  assert.match(presentation, /positive: 'مثبت', negative: 'منفی', neutral: 'خنثی'/);
});
