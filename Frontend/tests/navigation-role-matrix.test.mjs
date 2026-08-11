import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const workspacesPath = new URL('../src/app/workspaces.ts', import.meta.url);
const shellPath = new URL('../src/components/shell.ts', import.meta.url);

async function loadWorkspaces() {
  const source = await readFile(workspacesPath, 'utf8');
  const isolatedSource = source.replace(
    "import { policyManagementRoles } from './permissions.js';",
    "const policyManagementRoles = ['system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'student_affairs_deputy'];",
  );
  const output = ts.transpileModule(isolatedSource, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(output).toString('base64')}`;
  return import(moduleUrl);
}

test('staff navigation is the stable union of every role-authorized workspace', async () => {
  const { staffNavigationForRoles, staffWorkspaces } = await loadWorkspaces();
  const idsFor = roles => staffNavigationForRoles(roles).map(workspace => workspace.id);

  assert.equal(staffWorkspaces.length, 8);
  assert.deepEqual(idsFor([]), ['home']);
  assert.deepEqual(idsFor(['teacher']), ['home', 'students', 'education', 'attendance', 'reports']);
  assert.deepEqual(idsFor(['operator']), ['home', 'reports', 'data-center']);
  assert.deepEqual(
    idsFor(['school_manager']),
    ['home', 'students', 'education', 'attendance', 'follow-up', 'reports', 'data-center', 'administration'],
  );
  assert.deepEqual(
    idsFor(['teacher', 'operator']),
    ['home', 'students', 'education', 'attendance', 'reports', 'data-center'],
  );
  assert.deepEqual(
    idsFor(['educational_deputy']),
    ['home', 'students', 'education', 'attendance', 'follow-up', 'reports', 'data-center', 'administration'],
  );
  assert.deepEqual(
    idsFor(['student_affairs_deputy']),
    ['home', 'students', 'attendance', 'follow-up', 'administration'],
  );
  assert.deepEqual(idsFor(['counselor']), ['home', 'students', 'follow-up']);
  assert.deepEqual(idsFor(['guide_teacher']), ['home', 'students', 'follow-up']);
  assert.deepEqual(
    idsFor(['teacher', 'guide_teacher']),
    ['home', 'students', 'education', 'attendance', 'follow-up', 'reports'],
  );
  assert.deepEqual(
    idsFor(['school_manager', 'counselor']),
    ['home', 'students', 'education', 'attendance', 'follow-up', 'reports', 'data-center', 'administration'],
  );
});

test('reports and imports match their backend role policies', async () => {
  const { reportWorkspaceRoles, dataCenterWorkspaceRoles } = await loadWorkspaces();

  assert.deepEqual(reportWorkspaceRoles, [
    'system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'operator', 'teacher',
  ]);
  assert.deepEqual(dataCenterWorkspaceRoles, [
    'system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'operator',
  ]);
  assert.ok(!reportWorkspaceRoles.includes('student_affairs_deputy'));
});

test('topbar affordances follow visible workspaces and use the attendance alert route', async () => {
  const shell = await readFile(shellPath, 'utf8');

  assert.match(shell, /const visibleWorkspaceIds = new Set\(visibleNavigation\.map\(workspace => workspace\.id\)\)/);
  assert.match(shell, /const studentSearch = visibleWorkspaceIds\.has\('students'\)/);
  assert.match(shell, /visibleWorkspaceIds\.has\('attendance'\) && h\('button'/);
  assert.match(shell, /onClick: \(\) => navigate\('\/attendance\/alerts'\)/);
  assert.doesNotMatch(shell, /onClick: \(\) => navigate\('\/alerts'\)/);
});
