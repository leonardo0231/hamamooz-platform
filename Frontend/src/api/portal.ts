import { apiRequest } from './client.js';
import { endpoints } from './endpoints.js';

export interface PortalStudent {
  id: string;
  full_name: string;
  status: string;
}

export interface PortalReport {
  id: string;
  report_type: string;
  output_format: 'pdf' | 'docx';
  term: string;
  created_at: string;
  released_at: string;
}

export interface PortalRecommendation {
  id: string;
  priority: string;
  approved_text: string;
  approved_at: string;
}

export interface PortalAttendance {
  finalized_session_count: number;
  unexcused_absence_count: number;
  excused_absence_count: number;
}

export interface PortalGuidePlan {
  id: string;
  title: string;
  objectives: string;
  released_at: string;
}

export interface PortalSnapshot {
  reports: PortalReport[];
  recommendations: PortalRecommendation[];
  attendance: PortalAttendance;
  guidePlans: PortalGuidePlan[];
}

export const portalApi = {
  children: (): Promise<{ children: PortalStudent[] }> => apiRequest(endpoints.portal.children),
  childSnapshot: async (studentId: string): Promise<PortalSnapshot> => {
    const [reports, recommendations, attendance, guidePlans] = await Promise.all([
      apiRequest<{ reports: PortalReport[] }>(endpoints.portal.childReports(studentId)),
      apiRequest<{ recommendations: PortalRecommendation[] }>(endpoints.portal.childRecommendations(studentId)),
      apiRequest<PortalAttendance>(endpoints.portal.childAttendance(studentId)),
      apiRequest<{ guide_plans: PortalGuidePlan[] }>(endpoints.portal.childGuidePlans(studentId)),
    ]);
    return { reports: reports.reports, recommendations: recommendations.recommendations, attendance, guidePlans: guidePlans.guide_plans };
  },
  studentSnapshot: async (): Promise<PortalSnapshot> => {
    const [reports, recommendations, attendance, guidePlans] = await Promise.all([
      apiRequest<{ reports: PortalReport[] }>(endpoints.portal.studentReports),
      apiRequest<{ recommendations: PortalRecommendation[] }>(endpoints.portal.studentRecommendations),
      apiRequest<PortalAttendance>(endpoints.portal.studentAttendance),
      apiRequest<{ guide_plans: PortalGuidePlan[] }>(endpoints.portal.studentGuidePlans),
    ]);
    return { reports: reports.reports, recommendations: recommendations.recommendations, attendance, guidePlans: guidePlans.guide_plans };
  },
  downloadChildReport: (studentId: string, reportId: string): Promise<Blob> => (
    apiRequest<Blob>(endpoints.portal.childReportDownload(studentId, reportId), { responseType: 'blob' })
  ),
  downloadStudentReport: (reportId: string): Promise<Blob> => (
    apiRequest<Blob>(endpoints.portal.studentReportDownload(reportId), { responseType: 'blob' })
  ),
};
