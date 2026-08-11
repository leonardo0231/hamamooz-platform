import { apiRequest } from './client.js';
import { operationById } from './contract.js';
import { endpoints } from './endpoints.js';

export type RoleDashboardKind =
  | 'manager'
  | 'educational'
  | 'studentAffairs'
  | 'counselor'
  | 'guideTeacher'
  | 'teacher';

export interface RoleDashboard {
  dashboard: string;
  scope_school_ids: string[];
  metrics: Record<string, number>;
  drill_down: Record<string, string>;
}

const endpointFor: Record<RoleDashboardKind, string> = {
  manager: endpoints.dashboard.manager,
  educational: endpoints.dashboard.educational,
  studentAffairs: endpoints.dashboard.studentAffairs,
  counselor: endpoints.dashboard.counselor,
  guideTeacher: endpoints.dashboard.guideTeacher,
  teacher: endpoints.dashboard.teacher,
};

function operationPath(id: string): string {
  const operation = operationById(id);
  if (!operation) throw new Error(`API operation is missing from the generated contract: ${id}`);
  return operation.path;
}

// The reports page resolves this focused view through reports_drafts_list,
// whose response is ReportDraft rather than ReportArchive.
const reportDraftsRoute = '/reports?view=drafts';

/**
 * The backend returns a drill-down API path as part of its small read model.
 * Resolve those paths from operation IDs here, instead of copying API literals
 * into the page layer, so the generated contract remains the one source of truth.
 */
export const roleDashboardDrillDownRoutes: Record<string, string> = {
  [operationPath('analytics_operational_alerts_list')]: '/follow-up?view=operational-alerts',
  [operationPath('analytics_risk_signals_list')]: '/follow-up?view=risks',
  [operationPath('assessments_list')]: '/education?view=assessments',
  [operationPath('attendance_sessions_list')]: '/attendance?view=sessions',
  [operationPath('behavior_events_list')]: '/follow-up?view=behavior',
  [operationPath('counseling_cases_list')]: '/follow-up?view=counseling-cases',
  [operationPath('counseling_referrals_list')]: '/follow-up?view=counseling-referrals',
  [operationPath('guide_teacher_assignments_list')]: '/follow-up?view=guide-assignments',
  [operationPath('guide_follow_ups_list')]: '/follow-up?view=guide-follow-ups',
  [operationPath('reports_drafts_list')]: reportDraftsRoute,
};

export const roleDashboardApi = {
  get: (kind: RoleDashboardKind): Promise<RoleDashboard> => apiRequest<RoleDashboard>(endpointFor[kind]),
};
