const layouts = [
  ['analytical_term_1', 'کارنامه تحلیلی نوبت اول', 'analytical', 'first'],
  ['analytical_term_2', 'کارنامه تحلیلی نوبت دوم', 'analytical', 'second'],
  ['analytical_annual', 'کارنامه تحلیلی سالانه', 'analytical', 'annual'],
  ['final_term_1', 'کارنامه رسمی نوبت اول', 'final', 'first'],
  ['final_term_2', 'کارنامه رسمی نوبت دوم', 'final', 'second'],
  ['final_annual', 'کارنامه رسمی سالانه', 'final', 'annual'],
  ['summer_report', 'کارنامه دوره تابستان', 'summer', 'summer'],
];

export const REPORT_CARD_TEMPLATES = Object.freeze(layouts.map(([key, label, family, period]) => Object.freeze({
  key, label, family, period, pageSize: family === 'analytical' ? 'A3 landscape' : 'A4 portrait',
})));

export function reportTemplateByKey(key) {
  const template = REPORT_CARD_TEMPLATES.find(item => item.key === key);
  if (!template) throw new Error('قالب کارنامه انتخاب‌شده معتبر نیست.');
  return template;
}

export function buildReportTemplatePayload({ organization, school, templateKey }) {
  if (!organization || !school) throw new Error('مدرسه و مجموعه قالب باید مشخص باشند.');
  const layout = reportTemplateByKey(templateKey);
  const blocks = ['student_identity', 'academic_summary', 'signatures'];
  if (layout.family === 'analytical') blocks.splice(2, 0, 'attendance_summary', 'evaluation_radar', 'strengths', 'weaknesses', 'recommendations');
  return {
    organization, school, code: layout.key, title: layout.label,
    report_type: 'student_report_card', layout_key: layout.key, blocks,
    presentation: { page_size: layout.family === 'analytical' ? 'a3_landscape' : 'a4_portrait' },
  };
}

export function buildReportDraftPayload({ templateId, enrollmentId, templateKey, termId, summerRegistrationId, summerExamId }) {
  if (!templateId) throw new Error('انتخاب قالب کارنامه الزامی است.');
  const layout = reportTemplateByKey(templateKey);
  if (layout.family === 'summer') {
    if (!summerRegistrationId) throw new Error('ثبت‌نام دوره تابستان را انتخاب کنید.');
    return { template: templateId, summer_registration: summerRegistrationId, ...(summerExamId ? { summer_exam: summerExamId } : {}) };
  }
  if (!enrollmentId) throw new Error('انتخاب ثبت‌نام دانش‌آموز الزامی است.');
  if (layout.period === 'annual') return { template: templateId, enrollment: enrollmentId };
  if (!termId) throw new Error('انتخاب نوبت تحصیلی الزامی است.');
  return { template: templateId, enrollment: enrollmentId, term: termId };
}

function decimalString(value, message) {
  const normalized = String(value ?? '').trim();
  if (!/^(?:\d+\.?\d*|\.\d+)$/.test(normalized) || !Number.isFinite(Number(normalized))) throw new Error(message);
  return normalized;
}

export function normalizeAcademicSettingsPayload(values) {
  const invalid = 'وزن هر نوبت باید عددی معتبر و مثبت باشد.';
  const first = decimalString(values.firstTermWeight, invalid);
  const second = decimalString(values.secondTermWeight, invalid);
  if (Number(first) <= 0 || Number(second) <= 0) throw new Error(invalid);
  return {
    ...(values.school ? { school: values.school } : {}),
    ...(values.academicYear ? { academic_year: values.academicYear } : {}),
    first_term_weight: first,
    second_term_weight: second,
    show_class_rank: Boolean(values.showClassRank),
    show_grade_rank: Boolean(values.showGradeRank),
    show_school_rank: Boolean(values.showSchoolRank),
    ...(values.reason?.trim() ? { reason: values.reason.trim() } : {}),
  };
}

export function normalizeSummerThreshold(value) {
  if (value == null || String(value).trim() === '') return null;
  const message = 'حد نصاب تابستان باید بین ۰ تا ۲۰ باشد.';
  const normalized = decimalString(value, message);
  if (Number(normalized) < 0 || Number(normalized) > 20) throw new Error(message);
  return normalized;
}
