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

/**
 * The backend returns a drill-down API path as part of its small read model.
 * Resolve those paths from operation IDs here, instead of copying API literals
 * into the page layer, so the generated contract remains the one source of truth.
 */
export const roleDashboardDrillDownRoutes: Record<string, string> = {
  [operationPath('analytics_operational_alerts_list')]: '/resources/operational-alerts',
  [operationPath('analytics_risk_signals_list')]: '/resources/analytics-risk-signals',
  [operationPath('assessments_list')]: '/resources/assessments',
  [operationPath('attendance_sessions_list')]: '/resources/attendance-sessions',
  [operationPath('behavior_events_list')]: '/resources/behavior-events',
  [operationPath('counseling_cases_list')]: '/resources/counseling-cases',
  [operationPath('counseling_referrals_list')]: '/resources/counseling-referrals',
  [operationPath('guide_teacher_assignments_list')]: '/resources/guide-teacher-assignments',
  [operationPath('guide_follow_ups_list')]: '/resources/guide-follow-ups',
  [operationPath('reports_drafts_list')]: '/resources/report-drafts',
};

export const roleDashboardApi = {
  get: (kind: RoleDashboardKind): Promise<RoleDashboard> => apiRequest<RoleDashboard>(endpointFor[kind]),
};
