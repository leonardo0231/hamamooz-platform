import { actionRequestSchema } from '../api/action-schemas.js';
import { operationById } from '../api/contract.js';
import {
  student360Api,
  type Student360Academics,
  type Student360Activities,
  type Student360Attendance,
  type Student360Behavior,
  type Student360Evaluations,
  type Student360Recommendations,
  type Student360Reports,
  type Student360Risks,
  type Student360Summary,
  type StudentEvaluationAnalytics,
} from '../api/student-360.js';
import { studentsApi } from '../api/students.js';
import { navigate } from '../app/router.js';
import { broadEducationRoles, hasAnyRole, hasWriteScope } from '../app/permissions.js';
import { errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { openSchemaDialog, schemaHasBinary } from '../components/schema-form.js';
import { labelForValue } from '../ui/presentation.js';
import { clear, formatDate, formatNumber, h, initials, safeText } from '../utils/dom.js';

type Student360TabId =
  | 'summary'
  | 'academics'
  | 'attendance'
  | 'evaluations'
  | 'behavior'
  | 'activities'
  | 'risks'
  | 'recommendations'
  | 'reports';

interface Student360Tab {
  id: Student360TabId;
  label: string;
  load: () => Promise<HTMLElement>;
}

function emptySection(message: string, glyph = 'chart'): HTMLElement {
  return h('div', { className: 'inline-empty' }, icon(glyph), h('p', { text: message }));
}

function renderSummary(summary: Student360Summary): HTMLElement {
  const enrollment = summary.current_enrollment;
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h(
      'div',
      { className: 'card-header' },
      h('div', {}, h('h2', { text: 'خلاصه پرونده' }), h('p', { text: 'ترکیب فقط‌خواندنی از داده‌های مجاز دانش‌آموز' })),
      h('span', { className: 'card-icon' }, icon('user')),
    ),
    enrollment
      ? h(
        'dl',
        { className: 'detail-grid' },
        h('div', {}, h('dt', { text: 'شماره دانش‌آموزی' }), h('dd', { text: enrollment.student_number })),
        h('div', {}, h('dt', { text: 'مدرسه' }), h('dd', { text: enrollment.school })),
        h('div', {}, h('dt', { text: 'سال تحصیلی' }), h('dd', { text: enrollment.academic_year })),
        h('div', {}, h('dt', { text: 'پایه و کلاس' }), h('dd', { text: `${enrollment.grade} · ${enrollment.class_section}` })),
      )
      : emptySection('برای این دانش‌آموز ثبت‌نام قابل مشاهده‌ای وجود ندارد.', 'user'),
  );
}

function renderAcademics(academics: Student360Academics): HTMLElement {
  const termTable = academics.term_results.length
    ? h(
      'div',
      { className: 'table-wrap' },
      h(
        'table',
        { className: 'data-table' },
        h('thead', {}, h('tr', {}, ...['نوبت', 'میانگین', 'رتبه کلاس', 'وضعیت'].map(label => h('th', { scope: 'col', text: label })))),
        h(
          'tbody',
          {},
          ...academics.term_results.map(result => h(
            'tr',
            {},
            h('td', { dataset: { label: 'نوبت' }, text: result.term.title }),
            h('td', { dataset: { label: 'میانگین' }, text: result.average == null ? '—' : formatNumber(result.average) }),
            h('td', { dataset: { label: 'رتبه کلاس' }, text: result.class_rank == null ? '—' : formatNumber(result.class_rank) }),
            h('td', { dataset: { label: 'وضعیت' }, text: result.passed ? 'قبول' : 'نیازمند پیگیری' }),
          )),
        ),
      ),
    )
    : emptySection('هنوز نتیجه نوبت تحصیلی قابل مشاهده‌ای ثبت نشده است.');
  const subjectTable = academics.subject_results.length
    ? h(
      'div',
      { className: 'table-wrap' },
      h(
        'table',
        { className: 'data-table' },
        h('thead', {}, h('tr', {}, ...['درس', 'میانگین', 'وضعیت', 'نسخه فرمول'].map(label => h('th', { scope: 'col', text: label })))),
        h(
          'tbody',
          {},
          ...academics.subject_results.map(result => h(
            'tr',
            {},
            h('td', { dataset: { label: 'درس' }, text: result.subject }),
            h('td', { dataset: { label: 'میانگین' }, text: result.average == null ? '—' : formatNumber(result.average) }),
            h('td', { dataset: { label: 'وضعیت' }, text: result.passed ? 'قبول' : 'نیازمند پیگیری' }),
            h('td', { dataset: { label: 'نسخه فرمول' }, text: result.formula_version }),
          )),
        ),
      ),
    )
    : emptySection('هنوز نتیجه درس قابل مشاهده‌ای ثبت نشده است.');
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'وضعیت تحصیلی' }), h('p', { text: 'نتایج محاسبه‌شده و نسخه‌دار نوبت و درس‌ها' })), h('span', { className: 'card-icon' }, icon('chart'))),
    h('h3', { text: 'نتایج نوبت' }),
    termTable,
    h('h3', { text: 'نتایج درس' }),
    subjectTable,
  );
}

function renderAttendance(attendance: Student360Attendance): HTMLElement {
  if (!attendance.metrics) return emptySection('برای بازه تحصیلی قابل مشاهده، داده حضور و غیاب نهایی وجود ندارد.', 'check');
  const metrics = [
    ['جلسه ثبت‌شده', attendance.metrics.total_sessions],
    ['غیبت', attendance.metrics.absence_count],
    ['غیبت غیرموجه', attendance.metrics.unexcused_absence_count],
    ['تأخیر', attendance.metrics.late_count],
  ] as const;
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'حضور و غیاب' }), h('p', { text: `${formatDate(attendance.date_from)} تا ${formatDate(attendance.date_to)}` })), h('span', { className: 'card-icon' }, icon('check'))),
    h(
      'div',
      { className: 'metric-grid' },
      ...metrics.map(([label, value]) => h('div', { className: 'metric-card metric-card--border-blue' }, h('small', { text: label }), h('strong', { text: formatNumber(value) }))),
      h('div', { className: 'metric-card metric-card--border-orange' }, h('small', { text: 'درصد غیبت' }), h('strong', { text: `${formatNumber(attendance.metrics.absence_percent)}٪` })),
    ),
  );
}

function renderAnalytics(analytics: StudentEvaluationAnalytics): HTMLElement {
  return h(
    'article',
    { className: 'evaluation-analytics-card' },
    h('div', { className: 'card-header' }, h('div', {}, h('h3', { text: 'روند ارزیابی‌های نهایی' }), h('p', { text: analytics.completion_status === 'final' ? 'داده نهایی' : 'داده موقت' })), h('span', { className: 'card-icon' }, icon('chart'))),
    h(
      'div',
      { className: 'metric-grid' },
      h('div', { className: 'metric-card metric-card--border-purple' }, h('small', { text: 'امتیاز نهایی' }), h('strong', { text: analytics.overall_score == null ? '—' : `${formatNumber(analytics.overall_score)} از ۲۰` })),
      h('div', { className: 'metric-card metric-card--border-green' }, h('small', { text: 'درصد تکمیل' }), h('strong', { text: `${formatNumber(analytics.completion_percent)}٪` })),
      h('div', { className: 'metric-card metric-card--border-orange' }, h('small', { text: 'روند' }), h('strong', { text: analytics.trend_label })),
      h('div', { className: 'metric-card metric-card--border-blue' }, h('small', { text: 'رتبه در کلاس' }), h('strong', { text: analytics.rank == null ? '—' : `${formatNumber(analytics.rank)} از ${formatNumber(analytics.ranked_count)}` })),
    ),
    analytics.recommendation ? h('div', { className: 'student-notes' }, h('h4', { text: 'یادداشت تحلیلی' }), h('p', { text: analytics.recommendation })) : null,
  );
}

function renderEvaluations(evaluations: Student360Evaluations, analytics: StudentEvaluationAnalytics | null): HTMLElement {
  const table = evaluations.evaluations.length
    ? h(
      'div',
      { className: 'table-wrap' },
      h(
        'table',
        { className: 'data-table' },
        h('thead', {}, h('tr', {}, ...['ماه', 'امتیاز', 'تکمیل', 'شاخص‌های ثبت‌شده', 'آخرین تغییر'].map(label => h('th', { scope: 'col', text: label })))),
        h(
          'tbody',
          {},
          ...evaluations.evaluations.map(evaluation => h(
            'tr',
            {},
            h('td', { dataset: { label: 'ماه' }, text: formatNumber(evaluation.month_no) }),
            h('td', { dataset: { label: 'امتیاز' }, text: evaluation.overall_score == null ? '—' : `${formatNumber(evaluation.overall_score)} از ۲۰` }),
            h('td', { dataset: { label: 'تکمیل' }, text: `${formatNumber(evaluation.completion_percent)}٪` }),
            h('td', { dataset: { label: 'شاخص‌های ثبت‌شده' }, text: formatNumber(evaluation.metric_scores.length) }),
            h('td', { dataset: { label: 'آخرین تغییر' }, text: formatDate(evaluation.updated_at, true) }),
          )),
        ),
      ),
    )
    : emptySection('هنوز ارزیابی ماهانه‌ای برای این دانش‌آموز ثبت نشده است.');
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: '۷۴ شاخص ارزیابی' }), h('p', { text: `نسخه چارچوب ${evaluations.framework_version}` })), h('span', { className: 'card-icon' }, icon('chart'))),
    ...(analytics ? [renderAnalytics(analytics)] : []),
    table,
  );
}

function renderReports(reports: Student360Reports): HTMLElement {
  if (!reports.reports.length) return emptySection('گزارش رسمی دانش‌آموز در این حوزه وجود ندارد.', 'check');
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'گزارش‌های رسمی' }), h('p', { text: 'فقط آرشیوهای اختصاصی همین دانش‌آموز' })), h('span', { className: 'card-icon' }, icon('check'))),
    h(
      'div',
      { className: 'table-wrap' },
      h(
        'table',
        { className: 'data-table' },
        h('thead', {}, h('tr', {}, ...['نوع', 'وضعیت', 'نسخه فرمول', 'ایجاد', 'دریافت'].map(label => h('th', { scope: 'col', text: label })))),
        h(
          'tbody',
          {},
          ...reports.reports.map(report => h(
            'tr',
            {},
            h('td', { dataset: { label: 'نوع' }, text: safeText(report.report_type) }),
            h('td', { dataset: { label: 'وضعیت' }, text: safeText(report.status) }),
            h('td', { dataset: { label: 'نسخه فرمول' }, text: report.formula_version || '—' }),
            h('td', { dataset: { label: 'ایجاد' }, text: formatDate(report.created_at, true) }),
            h('td', { dataset: { label: 'دریافت' } }, report.download_url ? h('a', { className: 'button button--secondary', href: report.download_url, text: 'دریافت' }) : '—'),
          )),
        ),
      ),
    ),
  );
}

function renderBehavior(behavior: Student360Behavior): HTMLElement {
  if (!behavior.events.length) return emptySection('رویداد رفتاری قابل مشاهده‌ای برای این دانش‌آموز ثبت نشده است.', 'check');
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'رویدادهای رفتاری' }), h('p', { text: 'فقط واقعیت‌های ثبت‌شده نمایش داده می‌شوند؛ نمره ارزشیابی یا یادداشت محرمانه در این بخش نیست.' })), h('span', { className: 'card-icon' }, icon('check'))),
    h('div', { className: 'table-wrap', role: 'region', tabindex: '0', 'aria-label': 'جدول رویدادهای رفتاری' }, h(
      'table',
      { className: 'data-table' },
      h('thead', {}, h('tr', {}, ...['نوع', 'قطبیت', 'شدت', 'وضعیت'].map(label => h('th', { scope: 'col', text: label })))),
      h('tbody', {}, ...behavior.events.map(event => h(
        'tr',
        {},
        h('td', { dataset: { label: 'نوع' }, text: labelForValue(event.event_type) }),
        h('td', { dataset: { label: 'قطبیت' }, text: labelForValue(event.polarity) }),
        h('td', { dataset: { label: 'شدت' }, text: labelForValue(event.severity) }),
        h('td', { dataset: { label: 'وضعیت' }, text: labelForValue(event.status) }),
      ))),
    )),
  );
}

function renderActivities(activities: Student360Activities): HTMLElement {
  if (!activities.participations.length) return emptySection('مشارکت فعالیتی برای این دانش‌آموز ثبت نشده است.', 'chart');
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'فعالیت‌ها و دستاوردها' }), h('p', { text: 'مشارکت‌های فرهنگی، پژوهشی، ورزشی و هنری.' })), h('span', { className: 'card-icon' }, icon('chart'))),
    h('div', { className: 'table-wrap', role: 'region', tabindex: '0', 'aria-label': 'جدول فعالیت‌ها و دستاوردها' }, h(
      'table',
      { className: 'data-table' },
      h('thead', {}, h('tr', {}, ...['فعالیت', 'نوع', 'نقش', 'نتیجه', 'رتبه', 'وضعیت'].map(label => h('th', { scope: 'col', text: label })))),
      h('tbody', {}, ...activities.participations.map(participation => h(
        'tr',
        {},
        h('td', { dataset: { label: 'فعالیت' }, text: labelForValue(participation.activity) }),
        h('td', { dataset: { label: 'نوع' }, text: labelForValue(participation.kind) }),
        h('td', { dataset: { label: 'نقش' }, text: labelForValue(participation.participation_role) }),
        h('td', { dataset: { label: 'نتیجه' }, text: labelForValue(participation.result) }),
        h('td', { dataset: { label: 'رتبه' }, text: participation.placement == null ? '—' : formatNumber(participation.placement) }),
        h('td', { dataset: { label: 'وضعیت' }, text: labelForValue(participation.status) }),
      ))),
    )),
  );
}

function renderRisks(risks: Student360Risks): HTMLElement {
  if (!risks.signals.length) return emptySection('سیگنال ریسک فعالی برای این دانش‌آموز وجود ندارد.', 'chart');
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'سیگنال‌های ریسک' }), h('p', { text: 'خروجی قانون نسخه‌دار، قطعی و قابل توضیح.' })), h('span', { className: 'card-icon' }, icon('chart'))),
    h('div', { className: 'table-wrap', role: 'region', tabindex: '0', 'aria-label': 'جدول سیگنال‌های ریسک' }, h(
      'table',
      { className: 'data-table' },
      h('thead', {}, h('tr', {}, ...['قانون', 'نسخه', 'شدت', 'توضیح', 'ایجاد'].map(label => h('th', { scope: 'col', text: label })))),
      h('tbody', {}, ...risks.signals.map(signal => h(
        'tr',
        {},
        h('td', { dataset: { label: 'قانون' }, text: labelForValue(signal.rule_code) }),
        h('td', { dataset: { label: 'نسخه' }, text: formatNumber(signal.rule_version) }),
        h('td', { dataset: { label: 'شدت' }, text: labelForValue(signal.severity) }),
        h('td', { dataset: { label: 'توضیح' }, text: safeText(signal.explanation) }),
        h('td', { dataset: { label: 'ایجاد' }, text: formatDate(signal.created_at, true) }),
      ))),
    )),
  );
}

function renderRecommendations(recommendations: Student360Recommendations): HTMLElement {
  if (!recommendations.recommendations.length) return emptySection('توصیه‌ای برای این دانش‌آموز ثبت نشده است.', 'check');
  return h(
    'div',
    { className: 'student-360-panel__content' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'توصیه‌ها' }), h('p', { text: 'هر توصیه دارای وضعیت، مخاطب و نسخه قانون است.' })), h('span', { className: 'card-icon' }, icon('check'))),
    h('div', { className: 'table-wrap', role: 'region', tabindex: '0', 'aria-label': 'جدول توصیه‌ها' }, h(
      'table',
      { className: 'data-table' },
      h('thead', {}, h('tr', {}, ...['مخاطب', 'اولویت', 'وضعیت', 'قانون', 'متن'].map(label => h('th', { scope: 'col', text: label })))),
      h('tbody', {}, ...recommendations.recommendations.map(recommendation => h(
        'tr',
        {},
        h('td', { dataset: { label: 'مخاطب' }, text: labelForValue(recommendation.audience) }),
        h('td', { dataset: { label: 'اولویت' }, text: labelForValue(recommendation.priority) }),
        h('td', { dataset: { label: 'وضعیت' }, text: labelForValue(recommendation.status) }),
        h('td', { dataset: { label: 'قانون' }, text: `${labelForValue(recommendation.rule_code)} v${formatNumber(recommendation.rule_version)}` }),
        h('td', { dataset: { label: 'متن' }, text: safeText(recommendation.approved_text || recommendation.generated_text) }),
      ))),
    )),
  );
}

export async function renderStudentPage(id: string): Promise<HTMLElement> {
  const page = h('section', { className: 'page student-profile-page' });
  const content = h('div');
  page.append(
    h(
      'div',
      { className: 'page-heading' },
      h(
        'div',
        {},
        h('button', { className: 'back-link', type: 'button', onClick: () => navigate('/students') }, icon('chevron'), 'دانش‌آموزان'),
        h('h1', { text: 'نمای ۳۶۰ دانش‌آموز' }),
        h('p', { text: 'نمای یکپارچه و بخش‌بندی‌شده پرونده دانش‌آموز بر پایه قرارداد رسمی API' }),
      ),
    ),
    content,
  );

  async function load(): Promise<void> {
    clear(content);
    content.append(loadingState());
    try {
      const [student, summary] = await Promise.all([studentsApi.detail(id), student360Api.summary(id)]);
      clear(content);
      const canWrite = hasAnyRole(broadEducationRoles);
      const writeScopeReady = hasWriteScope();
      const editOperation = operationById('students_partial_update');
      const guardianOperation = operationById('students_guardians_create');
      const edit = (): void => {
        if (!editOperation) return;
        openSchemaDialog({
          title: 'ویرایش پرونده دانش‌آموز',
          schema: editOperation.requestSchema,
          initial: { ...student } as Record<string, unknown>,
          multipart: editOperation.requestMime === 'multipart/form-data' || schemaHasBinary(editOperation.requestSchema),
          submitLabel: 'ذخیره پرونده',
          onSubmit: async payload => {
            await studentsApi.update(id, payload);
            toast('پرونده دانش‌آموز به‌روزرسانی شد.', 'success');
            await load();
          },
        });
      };
      const attachGuardian = (): void => {
        if (!guardianOperation) return;
        openSchemaDialog({
          title: 'اتصال ولی به دانش‌آموز',
          schema: actionRequestSchema(guardianOperation),
          submitLabel: 'ثبت ارتباط',
          onSubmit: async payload => {
            await studentsApi.linkGuardian(id, payload);
            toast('ارتباط ولی ثبت شد.', 'success');
            await load();
          },
        });
      };
      const avatar = student.photo
        ? h('img', { className: 'student-avatar-image', src: student.photo, alt: `تصویر ${student.full_name}` })
        : h('span', { className: 'student-avatar-image student-avatar-image--initials', text: initials(student.full_name) });
      const hero = h(
        'article',
        { className: 'student-hero card' },
        avatar,
        h('div', { className: 'student-hero__identity' }, h('span', { className: `badge badge--${student.status === 'active' ? 'success' : 'neutral'}`, text: student.status === 'active' ? 'فعال' : student.status }), h('h2', { text: student.full_name }), h('p', { text: `کد ملی ${student.national_id}` })),
        canWrite ? h('div', { className: 'student-hero__actions' }, h('button', { className: 'button button--secondary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'ویرایش پرونده' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: edit }, icon('edit'), 'ویرایش پرونده'), h('button', { className: 'button button--primary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'اتصال ولی' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: attachGuardian }, icon('plus'), 'اتصال ولی')) : null,
      );
      const info = h(
        'article',
        { className: 'card student-info-card' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'اطلاعات هویتی' }), h('p', { text: 'داده ثبت‌شده در پرونده مرکزی' })), h('span', { className: 'card-icon' }, icon('user'))),
        h('dl', { className: 'detail-grid' }, h('div', {}, h('dt', { text: 'نام' }), h('dd', { text: student.first_name })), h('div', {}, h('dt', { text: 'نام خانوادگی' }), h('dd', { text: student.last_name })), h('div', {}, h('dt', { text: 'تاریخ تولد' }), h('dd', { text: formatDate(student.birth_date) })), h('div', {}, h('dt', { text: 'جنسیت' }), h('dd', { text: student.gender === 'female' ? 'دختر' : 'پسر' })), h('div', {}, h('dt', { text: 'مجموعه' }), h('dd', { text: student.organization_name })), h('div', {}, h('dt', { text: 'آخرین تغییر' }), h('dd', { text: formatDate(student.updated_at, true) }))),
        student.notes ? h('div', { className: 'student-notes' }, h('h3', { text: 'یادداشت پرونده' }), h('p', { text: student.notes })) : null,
      );
      const guardians = h(
        'article',
        { className: 'card guardians-card' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'اولیا و ارتباط‌ها' }), h('p', { text: `${student.guardians.length.toLocaleString('fa-IR')} ارتباط ثبت‌شده` })), h('span', { className: 'card-icon' }, icon('users'))),
        student.guardians.length
          ? h('div', { className: 'guardian-list' }, ...student.guardians.map(item => h('div', { className: 'guardian-item' }, h('span', { className: 'avatar avatar--soft', text: initials(String(item.guardian_name ?? 'ولی')) }), h('div', {}, h('strong', { text: safeText(item.guardian_name ?? item.guardian) }), h('small', { text: safeText(item.relationship) })), h('div', { className: 'guardian-flags' }, item.is_primary ? h('span', { className: 'badge badge--success', text: 'ولی اصلی' }) : null, item.can_pick_up ? h('span', { className: 'badge badge--neutral', text: 'مجاز به تحویل' }) : null))))
          : h('div', { className: 'inline-empty' }, icon('users'), h('p', { text: 'هنوز ولی‌ای به این پرونده متصل نشده است.' }), canWrite ? h('button', { className: 'button button--secondary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'اتصال ولی' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: attachGuardian }, icon('plus'), 'اتصال ولی') : null),
      );

      const tabPanel = h('div', { className: 'card student-360-panel', id: 'student-360-panel', role: 'tabpanel', tabindex: 0, 'aria-live': 'polite' });
      const tabList = h('div', { className: 'section-tabs', role: 'tablist', 'aria-label': 'بخش‌های پرونده دانش‌آموز' });
      const cachedPanels: Partial<Record<Student360TabId, HTMLElement>> = {};
      const tabButtons = new Map<Student360TabId, HTMLButtonElement>();
      let activeTab: Student360TabId = 'summary';
      let requestSequence = 0;
      const tabs: Student360Tab[] = [
        { id: 'summary', label: 'خلاصه', load: async () => renderSummary(summary) },
        { id: 'academics', label: 'تحصیلی', load: async () => renderAcademics(await student360Api.academics(id)) },
        { id: 'attendance', label: 'حضور و غیاب', load: async () => renderAttendance(await student360Api.attendance(id)) },
        {
          id: 'evaluations',
          label: '۷۴ شاخص',
          load: async () => {
            const evaluations = await student360Api.evaluations(id);
            const latest = evaluations.evaluations[0];
            const analytics = latest ? await student360Api.evaluationAnalytics(latest.enrollment) : null;
            return renderEvaluations(evaluations, analytics);
          },
        },
        { id: 'behavior', label: 'رفتار', load: async () => renderBehavior(await student360Api.behavior(id)) },
        { id: 'activities', label: 'فعالیت‌ها', load: async () => renderActivities(await student360Api.activities(id)) },
        { id: 'risks', label: 'ریسک', load: async () => renderRisks(await student360Api.risks(id)) },
        { id: 'recommendations', label: 'توصیه‌ها', load: async () => renderRecommendations(await student360Api.recommendations(id)) },
        { id: 'reports', label: 'گزارش‌ها', load: async () => renderReports(await student360Api.reports(id)) },
      ];
      const renderActiveTab = (tabId: Student360TabId): void => {
        for (const [candidateId, button] of tabButtons) {
          const selected = candidateId === tabId;
          button.classList.toggle('is-active', selected);
          button.setAttribute('aria-selected', selected ? 'true' : 'false');
          button.tabIndex = selected ? 0 : -1;
        }
        tabPanel.setAttribute('aria-labelledby', `student-360-tab-${tabId}`);
      };
      const activateTab = async (tabId: Student360TabId): Promise<void> => {
        activeTab = tabId;
        renderActiveTab(tabId);
        const token = ++requestSequence;
        const cached = cachedPanels[tabId];
        if (cached) {
          clear(tabPanel);
          tabPanel.append(cached);
          return;
        }
        clear(tabPanel);
        tabPanel.append(loadingState());
        const tab = tabs.find(candidate => candidate.id === tabId);
        if (!tab) return;
        try {
          const panel = await tab.load();
          cachedPanels[tabId] = panel;
          if (activeTab === tabId && requestSequence === token) {
            clear(tabPanel);
            tabPanel.append(panel);
          }
        } catch (error) {
          if (activeTab === tabId && requestSequence === token) {
            clear(tabPanel);
            tabPanel.append(errorState(error, () => void activateTab(tabId)));
          }
        }
      };
      for (const tab of tabs) {
        const button = h('button', { className: 'section-tab', type: 'button', id: `student-360-tab-${tab.id}`, role: 'tab', 'aria-controls': 'student-360-panel', 'aria-selected': tab.id === activeTab ? 'true' : 'false', tabindex: tab.id === activeTab ? 0 : -1, onClick: () => void activateTab(tab.id) });
        button.textContent = tab.label;
        tabButtons.set(tab.id, button);
        tabList.append(button);
      }
      const student360 = h('article', { className: 'card student-360-card' }, h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'نمای ۳۶۰ دانش‌آموز' }), h('p', { text: 'هر بخش تنها هنگام انتخاب بارگذاری می‌شود.' })), h('span', { className: 'card-icon' }, icon('chart'))), tabList, tabPanel);
      content.append(hero, h('div', { className: 'student-content-grid' }, info, guardians), student360);
      await activateTab('summary');
    } catch (error) {
      clear(content);
      content.append(errorState(error, () => void load()));
    }
  }

  await load();
  return page;
}
