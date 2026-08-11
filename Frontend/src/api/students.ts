import { apiRequest } from './client.js';
import { endpoints } from './endpoints.js';

export interface GuardianRelation {
  id?: string;
  guardian?: string;
  guardian_name?: string;
  relationship?: string;
  is_primary?: boolean;
  can_pick_up?: boolean;
  [key: string]: unknown;
}

export interface StudentProfile {
  id: string;
  organization: string;
  organization_name: string;
  national_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  birth_date: string;
  gender: string;
  status: string;
  photo?: string | null;
  notes?: string;
  guardians: GuardianRelation[];
  created_at: string;
  updated_at: string;
}

export const studentsApi = {
  detail: (id: string): Promise<StudentProfile> => apiRequest<StudentProfile>(endpoints.students.detail(id)),
  update: (id: string, payload: Record<string, unknown> | FormData): Promise<StudentProfile> => (
    apiRequest<StudentProfile>(endpoints.students.update(id), { method: 'PATCH', body: payload })
  ),
  linkGuardian: (id: string, payload: Record<string, unknown> | FormData): Promise<StudentProfile> => (
    apiRequest<StudentProfile>(endpoints.students.guardians(id), { method: 'POST', body: payload })
  ),
};
