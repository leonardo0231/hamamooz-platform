import { apiRequest } from './client.js';
import { endpoints } from './endpoints.js';

export interface Student360Summary {
  student: {
    id: string;
    full_name: string;
    status: string;
  };
  current_enrollment: {
    id: string;
    student_number: string;
    school: string;
    academic_year: string;
    grade: string;
    class_section: string;
    status: string;
  } | null;
}

export interface Student360Academics {
  term_results: Array<{
    enrollment: string;
    term: { id: string; title: string };
    average: number | null;
    class_rank: number | null;
    passed: boolean;
    formula_version: string;
  }>;
  subject_results: Array<{
    enrollment: string;
    subject: string;
    average: number | null;
    passed: boolean;
    formula_version: string;
  }>;
}

export interface Student360Attendance {
  enrollment: string | null;
  date_from: string | null;
  date_to: string | null;
  metrics: {
    total_sessions: number;
    absence_count: number;
    excused_absence_count: number;
    unexcused_absence_count: number;
    late_count: number;
    early_leave_count: number;
    absence_percent: number;
  } | null;
}

interface DomainScore {
  code: string;
  title: string;
  weight: number;
  score: number | null;
  completed_metrics: number;
}

export interface Student360Evaluation {
  id: string;
  enrollment: string;
  month_no: number;
  academic_year_title: string;
  class_title: string;
  overall_score: number | null;
  completion_percent: number;
  completion_status: 'provisional' | 'final';
  domain_scores: DomainScore[];
  note: string;
  updated_at: string;
  metric_scores: Array<{
    metric_code: string;
    title: string;
    domain_code: string;
    domain_title: string;
    value: number;
  }>;
}

export interface StudentEvaluationAnalytics {
  completion_status: 'provisional' | 'final';
  completion_percent: number;
  overall_score: number | null;
  performance_level: string | null;
  first_month: number | null;
  last_month: number | null;
  change: number | null;
  trend_label: string;
  strongest_domain: { code: string; title: string; score: number | null } | null;
  weakest_domain: { code: string; title: string; score: number | null } | null;
  recommendation: string | null;
  completion_warning: string | null;
  rank: number | null;
  ranked_count: number;
}

export interface Student360Evaluations {
  framework_version: string;
  evaluations: Student360Evaluation[];
}

export interface Student360Reports {
  reports: Array<{
    id: string;
    report_type: string;
    status: string;
    enrollment: string | null;
    formula_version: string;
    download_url: string | null;
    created_at: string;
  }>;
}

export interface Student360Behavior {
  events: Array<{
    id: string;
    event_type: string;
    polarity: string;
    severity: string;
    status: string;
  }>;
}

export interface Student360Activities {
  participations: Array<{
    id: string;
    activity: string;
    kind: string;
    status: string;
    participation_role: string;
    result: string;
    placement: number | null;
  }>;
}

export interface Student360Risks {
  signals: Array<{
    id: string;
    rule_code: string;
    rule_version: number;
    severity: string;
    evidence: Record<string, unknown>;
    explanation: string;
    window: Record<string, unknown>;
    created_at: string;
  }>;
}

export interface Student360Recommendations {
  recommendations: Array<{
    id: string;
    audience: string;
    priority: string;
    status: string;
    rule_code: string;
    rule_version: number;
    generated_text: string;
    approved_text: string;
    approved_at: string | null;
  }>;
}

export const student360Api = {
  summary: (id: string): Promise<Student360Summary> => apiRequest<Student360Summary>(endpoints.students.summary(id)),
  academics: (id: string): Promise<Student360Academics> => apiRequest<Student360Academics>(endpoints.students.academics(id)),
  attendance: (id: string): Promise<Student360Attendance> => apiRequest<Student360Attendance>(endpoints.students.attendance(id)),
  evaluations: (id: string): Promise<Student360Evaluations> => apiRequest<Student360Evaluations>(endpoints.students.evaluations(id)),
  reports: (id: string): Promise<Student360Reports> => apiRequest<Student360Reports>(endpoints.students.reports(id)),
  behavior: (id: string): Promise<Student360Behavior> => apiRequest<Student360Behavior>(endpoints.students.behavior(id)),
  activities: (id: string): Promise<Student360Activities> => apiRequest<Student360Activities>(endpoints.students.activities(id)),
  risks: (id: string): Promise<Student360Risks> => apiRequest<Student360Risks>(endpoints.students.risks(id)),
  recommendations: (id: string): Promise<Student360Recommendations> => apiRequest<Student360Recommendations>(endpoints.students.recommendations(id)),
  evaluationAnalytics: (enrollment: string): Promise<StudentEvaluationAnalytics> => (
    apiRequest<StudentEvaluationAnalytics>(endpoints.monthlyEvaluations.analytics, {
      query: { enrollment, rank_scope: 'class' },
    })
  ),
};
