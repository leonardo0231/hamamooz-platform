import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { operationById } from '../api/contract.js';
import { actionRequestSchema } from '../api/action-schemas.js';
import { navigate } from '../app/router.js';
import { broadEducationRoles, hasAnyRole, hasWriteScope } from '../app/permissions.js';
import type { Pagination } from '../api/types.js';
import { h, clear, formatDate, formatNumber, initials, safeText } from '../utils/dom.js';
import { errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { openSchemaDialog, schemaHasBinary } from '../components/schema-form.js';

interface GuardianRelation {
  id?: string;
  guardian?: string;
  guardian_name?: string;
  relationship?: string;
  is_primary?: boolean;
  can_pick_up?: boolean;
  [key: string]: unknown;
}

interface Student {
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

interface DomainScore {
  code: string;
  title: string;
  weight: number;
  score: string | number | null;
  completed_metrics: number;
}

interface MonthlyEvaluation {
  id: string;
  enrollment: string;
  month_no: number;
  academic_year_title: string;
  class_title: string;
  overall_score: string | number | null;
  completion_percent: string | number;
  domain_scores: DomainScore[];
  note: string;
  updated_at: string;
}

interface AnalyticsDomain {
  code: string;
  title: string;
  score: number | null;
}

interface StudentEvaluationAnalytics {
  completion_status: 'provisional' | 'final';
  completion_percent: number;
  overall_score: number | null;
  performance_level: string | null;
  first_month: number | null;
  last_month: number | null;
  change: number | null;
  trend_label: string;
  strongest_domain: AnalyticsDomain | null;
  weakest_domain: AnalyticsDomain | null;
  recommendation: string | null;
  completion_warning: string | null;
  rank: number | null;
  ranked_count: number;
}

export async function renderStudentPage(id: string): Promise<HTMLElement> {
  const page = h('section', { className: 'page student-profile-page' });
  const content = h('div');
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('button', { className: 'back-link', type: 'button', onClick: () => navigate('/students') }, icon('chevron'), 'دانش‌آموزان'), h('h1', { text: 'پرونده دانش‌آموز' }), h('p', { text: 'اطلاعات پرونده و ارتباط با اولیا براساس API رسمی' }))), content);

  async function load(): Promise<void> {
    clear(content); content.append(loadingState());
    try {
      const [student, evaluations] = await Promise.all([
        apiRequest<Student>(endpoints.students.detail(id)),
        apiRequest<Pagination<MonthlyEvaluation>>(endpoints.monthlyEvaluations.list, {
          query: { enrollment__student: id, page_size: 24, ordering: '-month_no' },
        }),
      ]);
      const analytics = evaluations.results[0]
        ? await apiRequest<StudentEvaluationAnalytics>(endpoints.monthlyEvaluations.analytics, {
          query: { enrollment: evaluations.results[0].enrollment, rank_scope: 'class' },
        })
        : null;
      clear(content);
      const editOperation = operationById('students_partial_update');
      const guardianOperation = operationById('students_guardians_create');
      const canWrite = hasAnyRole(broadEducationRoles);
      const writeScopeReady = hasWriteScope();
      const edit = (): void => {
        if (!editOperation) return;
        openSchemaDialog({
          title: 'ویرایش پرونده دانش‌آموز', schema: editOperation.requestSchema, initial: { ...student } as Record<string, unknown>, multipart: editOperation.requestMime === 'multipart/form-data' || schemaHasBinary(editOperation.requestSchema), submitLabel: 'ذخیره پرونده',
          onSubmit: async payload => { await apiRequest(endpoints.students.update(id), { method: 'PATCH', body: payload }); toast('پرونده دانش‌آموز به‌روزرسانی شد.', 'success'); await load(); },
        });
      };
      const attachGuardian = (): void => {
        if (!guardianOperation) return;
        openSchemaDialog({
          title: 'اتصال ولی به دانش‌آموز', schema: actionRequestSchema(guardianOperation), submitLabel: 'ثبت ارتباط',
          onSubmit: async payload => { await apiRequest(endpoints.students.guardians(id), { method: 'POST', body: payload }); toast('ارتباط ولی ثبت شد.', 'success'); await load(); },
        });
      };
      const avatar = student.photo
        ? h('img', { className: 'student-avatar-image', src: student.photo, alt: `تصویر ${student.full_name}` })
        : h('span', { className: 'student-avatar-image student-avatar-image--initials', text: initials(student.full_name) });
      const hero = h('article', { className: 'student-hero card' }, avatar,
        h('div', { className: 'student-hero__identity' }, h('span', { className: `badge badge--${student.status === 'active' ? 'success' : 'neutral'}`, text: student.status === 'active' ? 'فعال' : student.status }), h('h2', { text: student.full_name }), h('p', { text: `کد ملی ${student.national_id}` })),
        canWrite ? h('div', { className: 'student-hero__actions' },
          h('button', { className: 'button button--secondary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'ویرایش پرونده' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: edit }, icon('edit'), 'ویرایش پرونده'),
          h('button', { className: 'button button--primary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'اتصال ولی' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: attachGuardian }, icon('plus'), 'اتصال ولی'),
        ) : null,
      );
      const info = h('article', { className: 'card student-info-card' }, h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'اطلاعات هویتی' }), h('p', { text: 'اطلاعات ثبت‌شده در پرونده مرکزی' })), h('span', { className: 'card-icon' }, icon('user'))),
        h('dl', { className: 'detail-grid' },
          h('div', {}, h('dt', { text: 'نام' }), h('dd', { text: student.first_name })), h('div', {}, h('dt', { text: 'نام خانوادگی' }), h('dd', { text: student.last_name })),
          h('div', {}, h('dt', { text: 'تاریخ تولد' }), h('dd', { text: formatDate(student.birth_date) })), h('div', {}, h('dt', { text: 'جنسیت' }), h('dd', { text: student.gender === 'female' ? 'دختر' : 'پسر' })),
          h('div', {}, h('dt', { text: 'مجموعه' }), h('dd', { text: student.organization_name })), h('div', {}, h('dt', { text: 'آخرین تغییر' }), h('dd', { text: formatDate(student.updated_at, true) })),
        ), student.notes ? h('div', { className: 'student-notes' }, h('h3', { text: 'یادداشت پرونده' }), h('p', { text: student.notes })) : null);
      const guardians = h('article', { className: 'card guardians-card' }, h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'اولیا و ارتباط‌ها' }), h('p', { text: `${student.guardians.length.toLocaleString('fa-IR')} ارتباط ثبت‌شده` })), h('span', { className: 'card-icon' }, icon('users'))),
        student.guardians.length ? h('div', { className: 'guardian-list' }, ...student.guardians.map(item => h('div', { className: 'guardian-item' }, h('span', { className: 'avatar avatar--soft', text: initials(String(item.guardian_name ?? 'ولی')) }), h('div', {}, h('strong', { text: safeText(item.guardian_name ?? item.guardian) }), h('small', { text: safeText(item.relationship) })), h('div', { className: 'guardian-flags' }, item.is_primary ? h('span', { className: 'badge badge--success', text: 'ولی اصلی' }) : null, item.can_pick_up ? h('span', { className: 'badge badge--neutral', text: 'مجاز به تحویل' }) : null))))
          : h('div', { className: 'inline-empty' }, icon('users'), h('p', { text: 'هنوز ولی‌ای به این پرونده متصل نشده است.' }), canWrite ? h('button', { className: 'button button--secondary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'اتصال ولی' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: attachGuardian }, icon('plus'), 'اتصال ولی') : null));
      const evaluationSection = h('article', { className: 'card' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'ارزیابی جامع ماهانه' }), h('p', { text: `${formatNumber(evaluations.count)} ارزیابی ذخیره‌شده` })), h('span', { className: 'card-icon' }, icon('chart'))),
        evaluations.results.length
          ? h('div', { className: 'table-wrap' }, h('table', { className: 'data-table' },
            h('thead', {}, h('tr', {}, ...['سال/کلاس', 'ماه', 'امتیاز نهایی', 'تکمیل', 'امتیاز حیطه‌ها', 'آخرین تغییر'].map(label => h('th', { scope: 'col', text: label })))),
            h('tbody', {}, ...evaluations.results.map(evaluation => h('tr', {},
              h('td', { dataset: { label: 'سال/کلاس' }, text: `${evaluation.academic_year_title} · ${evaluation.class_title}` }),
              h('td', { dataset: { label: 'ماه' }, text: formatNumber(evaluation.month_no) }),
              h('td', { dataset: { label: 'امتیاز نهایی' }, text: evaluation.overall_score == null ? '—' : `${formatNumber(evaluation.overall_score)} از ۲۰` }),
              h('td', { dataset: { label: 'تکمیل' }, text: `${formatNumber(evaluation.completion_percent)}٪` }),
              h('td', { dataset: { label: 'حیطه‌ها' }, text: evaluation.domain_scores.filter(item => item.score != null).map(item => `${item.title}: ${formatNumber(item.score)}`).join(' | ') || '—' }),
              h('td', { dataset: { label: 'آخرین تغییر' }, text: formatDate(evaluation.updated_at, true) }),
            ))),
          ))
          : h('div', { className: 'inline-empty' }, icon('chart'), h('p', { text: 'هنوز ارزیابی ماهانه‌ای برای این دانش‌آموز ثبت نشده است.' })),
      );
      const analyticsSection = analytics ? h('article', { className: 'card evaluation-analytics-card' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'روند پیشرفت' }), h('p', { text: 'تحلیل محاسبه‌شده از ارزیابی‌های نهایی' })), h('span', { className: 'card-icon' }, icon('chart'))),
        h('div', { className: 'metric-grid' },
          h('div', { className: 'metric-card metric-card--border-purple' }, h('span', { className: 'metric-card__icon metric-card__icon--purple' }, icon('chart')), h('div', {}, h('small', { text: 'میانگین نهایی' }), h('strong', { text: analytics.overall_score == null ? '—' : `${formatNumber(analytics.overall_score)} از ۲۰` }), h('span', { text: analytics.performance_level ?? 'اطلاعات ناقص' }))),
          h('div', { className: 'metric-card metric-card--border-green' }, h('span', { className: 'metric-card__icon metric-card__icon--green' }, icon('check')), h('div', {}, h('small', { text: 'درصد تکمیل' }), h('strong', { text: `${formatNumber(analytics.completion_percent)}٪` }), h('span', { text: analytics.completion_status === 'final' ? 'نهایی' : 'موقت' }))),
          h('div', { className: 'metric-card metric-card--border-orange' }, h('span', { className: 'metric-card__icon metric-card__icon--orange' }, icon('chart')), h('div', {}, h('small', { text: 'روند' }), h('strong', { text: analytics.trend_label }), h('span', { text: analytics.change == null ? 'داده ناکافی' : `${analytics.change >= 0 ? '+' : ''}${formatNumber(analytics.change)} امتیاز` }))),
          h('div', { className: 'metric-card metric-card--border-purple' }, h('span', { className: 'metric-card__icon metric-card__icon--blue' }, icon('users')), h('div', {}, h('small', { text: 'رتبه در کلاس' }), h('strong', { text: analytics.rank == null ? '—' : `${formatNumber(analytics.rank)} از ${formatNumber(analytics.ranked_count)}` }), h('span', { text: analytics.rank == null ? 'فقط نتایج نهایی رتبه‌بندی می‌شوند' : 'براساس نتایج نهایی' }))),
        ),
        h('dl', { className: 'detail-grid' },
          h('div', {}, h('dt', { text: 'اولین تا آخرین ماه' }), h('dd', { text: analytics.first_month == null ? '—' : `${formatNumber(analytics.first_month)} تا ${formatNumber(analytics.last_month)}` })),
          h('div', {}, h('dt', { text: 'قوی‌ترین حیطه' }), h('dd', { text: analytics.strongest_domain ? `${analytics.strongest_domain.title}: ${formatNumber(analytics.strongest_domain.score)}` : '—' })),
          h('div', {}, h('dt', { text: 'ضعیف‌ترین حیطه' }), h('dd', { text: analytics.weakest_domain ? `${analytics.weakest_domain.title}: ${formatNumber(analytics.weakest_domain.score)}` : '—' })),
          h('div', {}, h('dt', { text: 'وضعیت نتیجه' }), h('dd', { text: analytics.completion_warning ?? 'اطلاعات کامل است.' })),
        ),
        analytics.recommendation ? h('div', { className: 'student-notes' }, h('h3', { text: 'پیشنهاد مداخله' }), h('p', { text: analytics.recommendation })) : null,
      ) : null;
      const contractNotice = h('article', { className: 'contract-notice' }, icon('check'), h('div', {}, h('strong', { text: 'داده مستقیم و قابل ردیابی' }), h('p', { text: 'ارزیابی‌های ماهانه از فایل معتبر ذخیره می‌شوند و امتیاز حیطه‌ها و نمره نهایی توسط Backend محاسبه می‌شود.' })));
      content.append(hero, h('div', { className: 'student-content-grid' }, info, guardians), ...(analyticsSection ? [analyticsSection] : []), evaluationSection, contractNotice);
    } catch (error) { clear(content); content.append(errorState(error, () => void load())); }
  }
  await load();
  return page;
}
