import type { ContractOperation, ContractSchema } from './contract.js';

const scoreStatuses = ['present', 'excused_absent', 'unexcused_absent', 'not_entered'];
const attendanceStatuses = ['present', 'absent_unexcused'];
const notificationChannels = ['in_app', 'email', 'sms'];
const guardianRelationships = ['father', 'mother', 'guardian', 'other'];

const empty: ContractSchema = { type: 'object', properties: {} };

/**
 * drf-spectacular currently infers several @action bodies from each ViewSet's
 * default ModelSerializer. These explicit schemas are transcribed from the
 * serializers used by the real action implementations in Backend/hamamooz.
 * Remove an override only after the generated OpenAPI operation is corrected.
 */
const overrides: Record<string, ContractSchema> = {
  assessments_approve_create: empty,
  assessments_lock_create: empty,
  assessments_submit_create: empty,
  assessments_reject_create: {
    type: 'object', required: ['reason'], properties: {
      reason: { type: 'string', minLength: 3, title: 'دلیل رد' },
    },
  },
  assessments_scores_bulk_create: {
    type: 'object', required: ['entries'], properties: {
      entries: {
        type: 'array', minItems: 1, title: 'ورودی‌های نمره', items: {
          type: 'object', required: ['enrollment', 'status'], properties: {
            enrollment: { type: 'string', format: 'uuid', title: 'ثبت‌نام' },
            value: { type: 'number', nullable: true, title: 'نمره' },
            status: { type: 'string', enum: scoreStatuses, title: 'وضعیت' },
            note: { type: 'string', maxLength: 500, title: 'یادداشت' },
          },
        },
      },
    },
  },
  scores_correct_locked_create: {
    type: 'object', required: ['status', 'reason'], properties: {
      value: { type: 'number', nullable: true, title: 'نمره' },
      status: { type: 'string', enum: scoreStatuses, title: 'وضعیت' },
      note: { type: 'string', maxLength: 500, title: 'یادداشت' },
      reason: { type: 'string', minLength: 5, title: 'دلیل اصلاح' },
    },
  },
  attendance_sessions_bulk_mark_create: {
    type: 'object', required: ['records'], properties: {
      records: {
        type: 'array', minItems: 1, title: 'رکوردهای حضور', items: {
          type: 'object', required: ['enrollment'], properties: {
            enrollment: { type: 'string', format: 'uuid', title: 'ثبت‌نام' },
            status: { type: 'string', enum: attendanceStatuses, default: 'present', title: 'وضعیت' },
            arrival_time: { type: 'string', format: 'time', nullable: true, title: 'زمان ورود' },
            departure_time: { type: 'string', format: 'time', nullable: true, title: 'زمان خروج' },
            late_minutes: { type: 'integer', minimum: 0, maximum: 1440, default: 0, title: 'دقایق تأخیر' },
            early_leave_minutes: { type: 'integer', minimum: 0, maximum: 1440, default: 0, title: 'دقایق خروج زودهنگام' },
            note: { type: 'string', maxLength: 500, title: 'یادداشت' },
          },
        },
      },
    },
  },
  attendance_sessions_finalize_create: empty,
  attendance_sessions_cancel_create: {
    type: 'object', required: ['reason'], properties: {
      reason: { type: 'string', minLength: 3, title: 'دلیل لغو' },
    },
  },
  attendance_records_correct_create: {
    type: 'object', required: ['reason'], properties: {
      status: { type: 'string', enum: attendanceStatuses, title: 'وضعیت' },
      arrival_time: { type: 'string', format: 'time', nullable: true, title: 'زمان ورود' },
      departure_time: { type: 'string', format: 'time', nullable: true, title: 'زمان خروج' },
      late_minutes: { type: 'integer', minimum: 0, maximum: 1440, title: 'دقایق تأخیر' },
      early_leave_minutes: { type: 'integer', minimum: 0, maximum: 1440, title: 'دقایق خروج زودهنگام' },
      note: { type: 'string', maxLength: 500, title: 'یادداشت' },
      reason: { type: 'string', minLength: 3, maxLength: 1000, title: 'دلیل اصلاح' },
    },
  },
  attendance_records_submit_excuse_create: {
    type: 'object', required: ['reason'], properties: {
      reason: { type: 'string', minLength: 3, maxLength: 2000, title: 'دلیل غیبت' },
      evidence_files: { type: 'array', maxItems: 5, title: 'مدارک', items: { type: 'string', format: 'binary' } },
    },
  },
  attendance_records_approve_excuse_create: {
    type: 'object', properties: { note: { type: 'string', maxLength: 2000, title: 'یادداشت بررسی' } },
  },
  attendance_records_reject_excuse_create: {
    type: 'object', properties: { note: { type: 'string', maxLength: 2000, title: 'یادداشت بررسی' } },
  },
  attendance_records_notify_guardians_create: {
    type: 'object', properties: {
      channels: { type: 'array', minItems: 1, title: 'کانال‌های اعلان', items: { type: 'string', enum: notificationChannels } },
    },
  },
  attendance_alerts_acknowledge_create: empty,
  attendance_alerts_resolve_create: empty,
  attendance_alerts_evaluate_create: {
    type: 'object', required: ['policy'], properties: { policy: { type: 'string', format: 'uuid', title: 'سیاست حضور' } },
  },
  enrollments_change_class_create: {
    type: 'object', required: ['class_section', 'reason'], properties: {
      class_section: { type: 'string', format: 'uuid', title: 'کلاس جدید' },
      effective_date: { type: 'string', format: 'date', title: 'تاریخ اثر' },
      reason: { type: 'string', minLength: 3, title: 'دلیل' },
    },
  },
  enrollments_transfer_create: {
    type: 'object', required: ['school', 'grade_level', 'class_section', 'student_number', 'transfer_date', 'reason'], properties: {
      school: { type: 'string', format: 'uuid', title: 'مدرسه مقصد' },
      grade_level: { type: 'string', format: 'uuid', title: 'پایه مقصد' },
      class_section: { type: 'string', format: 'uuid', title: 'کلاس مقصد' },
      student_number: { type: 'string', maxLength: 50, title: 'شماره دانش‌آموزی' },
      transfer_date: { type: 'string', format: 'date', title: 'تاریخ انتقال' },
      reason: { type: 'string', minLength: 3, title: 'دلیل انتقال' },
    },
  },
  enrollments_change_status_create: {
    type: 'object', required: ['status', 'date', 'reason'], properties: {
      status: { type: 'string', enum: ['withdrawn', 'graduated'], title: 'وضعیت جدید' },
      date: { type: 'string', format: 'date', title: 'تاریخ' },
      reason: { type: 'string', minLength: 3, title: 'دلیل' },
    },
  },
  students_guardians_create: {
    type: 'object', required: ['guardian', 'relationship'], properties: {
      guardian: { type: 'string', format: 'uuid', title: 'ولی' },
      relationship: { type: 'string', enum: guardianRelationships, title: 'نسبت' },
      is_primary: { type: 'boolean', default: false, title: 'ولی اصلی' },
      can_pick_up: { type: 'boolean', default: false, title: 'مجاز به تحویل‌گرفتن' },
    },
  },
  users_change_password_create: {
    type: 'object', required: ['new_password'], properties: {
      current_password: { type: 'string', format: 'password', title: 'رمز فعلی' },
      new_password: { type: 'string', format: 'password', title: 'رمز جدید' },
    },
  },
  users_deactivate_create: empty,
  imports_retry_create: empty,
  parent_notifications_retry_create: empty,
  reports_preview_create: {
    type: 'object', required: ['report_type', 'term'], properties: {
      report_type: { type: 'string', enum: ['student_report_card', 'class_report_cards'], title: 'نوع گزارش' },
      term: { type: 'string', format: 'uuid', title: 'نوبت' },
      enrollment: { type: 'string', format: 'uuid', nullable: true, title: 'ثبت‌نام دانش‌آموز' },
      class_section: { type: 'string', format: 'uuid', nullable: true, title: 'کلاس' },
    },
  },
};

export function actionRequestSchema(operation: ContractOperation): ContractSchema {
  return overrides[operation.id] ?? operation.requestSchema;
}

export function hasActionSchemaOverride(operationId: string): boolean {
  return Object.hasOwn(overrides, operationId);
}
