export type Primitive = string | number | boolean | null;
export type JsonValue = Primitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export interface Pagination<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface RoleAssignment {
  id: string;
  user: number;
  organization: string | null;
  school: string | null;
  role: Role;
  role_display?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export type Role =
  | 'system_admin'
  | 'organization_admin'
  | 'school_manager'
  | 'educational_deputy'
  | 'operator'
  | 'teacher'
  | 'student_affairs_deputy'
  | 'counselor'
  | 'guide_teacher';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  national_id?: string | null;
  is_active: boolean;
  must_change_password?: boolean;
  role_assignments: RoleAssignment[];
  last_login?: string | null;
  date_joined?: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user?: Pick<User, 'id' | 'username' | 'email' | 'first_name' | 'last_name' | 'is_active'>;
}

export interface RefreshResponse {
  access: string;
  refresh?: string;
}

export interface ScopeState {
  organizationId: string | null;
  schoolId: string | null;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    detail?: unknown;
    request_id?: string;
  };
  detail?: unknown;
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: unknown;
  readonly requestId: string | undefined;
  readonly fieldErrors: Record<string, string[]>;

  constructor(input: {
    status: number;
    code?: string;
    message: string;
    detail?: unknown;
    requestId?: string | undefined;
    fieldErrors?: Record<string, string[]>;
  }) {
    super(input.message);
    this.name = 'ApiError';
    this.status = input.status;
    this.code = input.code ?? 'error';
    this.detail = input.detail;
    this.requestId = input.requestId;
    this.fieldErrors = input.fieldErrors ?? {};
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  query?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
  auth?: boolean;
  retryAuth?: boolean;
  responseType?: 'json' | 'blob' | 'text' | 'void';
  onUploadProgress?: (percent: number) => void;
}
