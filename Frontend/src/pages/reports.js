import { html, useEffect, useMemo, useState } from '../core/view.js';
import { reportApi } from '../core/api.js';
import { useAsyncData } from '../core/hooks.js';
import { hasRole, useStore } from '../core/store.js';
import {
  REPORT_CARD_TEMPLATES, buildReportDraftPayload, buildReportTemplatePayload, normalizeAcademicSettingsPayload,
  normalizeSummerThreshold, reportTemplateByKey,
} from '../core/report-cards.js';
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, Skeleton } from '../components/ui.js';

const managers = ['system_admin', 'organization_admin', 'school_manager', 'educational_deputy'];
const list = value => Array.isArray(value) ? value : value?.results ?? [];
const date = value => value ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium' }).format(new Date(value)) : '—';
const selectedOrganization = (user, schoolId) => user?.role_assignments?.find(item => item.is_active && (!item.school || item.school === schoolId))?.organization;

function Notice({ notice }) {
  if (!notice) return null;
  return html`<p class=${`report-notice report-notice--${notice.kind}`} role="status">${notice.message}</p>`;
}

function Field({ label, children, hint }) {
  return html`<label class="report-field"><span>${label}</span>${children}${hint && html`<small>${hint}</small>`}</label>`;
}

function useWorkspace(yearId, schoolId) {
  return useAsyncData(async signal => {
    const query = { page_size: 100, ...(yearId ? { academic_year: yearId } : {}), ...(schoolId ? { school: schoolId } : {}) };
    const resources = {
      academicYears: () => reportApi.academicYears({ page_size: 100 }, signal),
      terms: () => reportApi.terms(query, signal),
      enrollments: () => reportApi.enrollments({ ...query, status: 'active' }, signal),
      subjects: () => reportApi.subjects({ page_size: 100 }, signal),
      templates: () => reportApi.templates(query, signal),
      drafts: () => reportApi.drafts(query, signal),
      archives: () => reportApi.archives(query, signal),
      settings: () => reportApi.settings(query, signal),
      summerPrograms: () => reportApi.summerPrograms(query, signal),
      summerCourses: () => reportApi.summerCourses(query, signal),
      summerRegistrations: () => reportApi.summerRegistrations(query, signal),
      summerCourseRegistrations: () => reportApi.summerCourseRegistrations(query, signal),
      summerExams: () => reportApi.summerExams(query, signal),
      summerScores: () => reportApi.summerScores(query, signal),
    };
    const entries = Object.entries(resources);
    const responses = await Promise.allSettled(entries.map(([, load]) => load()));
    const firstRequiredFailure = responses.find((response, index) => response.status === 'rejected' && ['academicYears', 'enrollments'].includes(entries[index][0]));
    if (firstRequiredFailure) throw firstRequiredFailure.reason;
    return Object.fromEntries(responses.map((response, index) => [entries[index][0], response.status === 'fulfilled' ? list(response.value) : []]));
  }, [yearId, schoolId]);
}

function AcademicSettings({ current, schoolId, yearId, reload, notify }) {
  const [values, setValues] = useState({ firstTermWeight: '1', secondTermWeight: '2', showClassRank: true, showGradeRank: true, showSchoolRank: true, reason: '' });
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (current) setValues({
      firstTermWeight: String(current.first_term_weight), secondTermWeight: String(current.second_term_weight),
      showClassRank: current.show_class_rank, showGradeRank: current.show_grade_rank,
      showSchoolRank: current.show_school_rank, reason: '',
    });
  }, [current?.id, current?.updated_at]);
  const change = (key, value) => setValues(previous => ({ ...previous, [key]: value }));
  const save = async event => {
    event.preventDefault();
    setSaving(true);
    try {
      if (!schoolId || !yearId) throw new Error('ابتدا مدرسه و سال تحصیلی را انتخاب کنید.');
      const payload = normalizeAcademicSettingsPayload({ ...values, school: schoolId, academicYear: yearId });
      if (current) {
        if ((payload.reason ?? '').length < 5) throw new Error('برای تغییر سیاست آموزشی علت تغییر را با حداقل پنج نویسه وارد کنید.');
        await reportApi.updateSettings(current.id, payload);
      } else {
        const { reason, ...creationPayload } = payload;
        await reportApi.createSettings(creationPayload);
      }
      notify({ kind: 'success', message: 'وزن نوبت‌ها و تنظیم نمایش رتبه‌ها با ثبت تاریخچه ذخیره شد.' });
      await reload();
    } catch (error) { notify({ kind: 'error', message: error.message }); }
    finally { setSaving(false); }
  };
  return html`<${Card} className="report-card" title="سیاست محاسبه سالانه و نمایش رتبه‌ها" subtitle="تغییر سیاست فقط بر محاسبه‌های بعدی اثر دارد و نسخه‌های صادرشده را تغییر نمی‌دهد.">
    <form class="report-form" onSubmit=${save}>
      <div class="report-grid report-grid--three">
        <${Field} label="وزن نوبت اول"><input inputmode="decimal" value=${values.firstTermWeight} onInput=${event => change('firstTermWeight', event.currentTarget.value)} required/></${Field}>
        <${Field} label="وزن نوبت دوم"><input inputmode="decimal" value=${values.secondTermWeight} onInput=${event => change('secondTermWeight', event.currentTarget.value)} required/></${Field}>
        <${Field} label="علت تغییر"><input value=${values.reason} onInput=${event => change('reason', event.currentTarget.value)} placeholder="مثلاً مصوبه شورای آموزشی"/></${Field}>
      </div>
      <div class="report-switches">${[['showClassRank', 'نمایش رتبه کلاس'], ['showGradeRank', 'نمایش رتبه پایه'], ['showSchoolRank', 'نمایش رتبه مدرسه']].map(([key, title]) => html`<label key=${key} class="report-switch"><input type="checkbox" checked=${values[key]} onChange=${event => change(key, event.currentTarget.checked)}/><span>${title}</span></label>`)}</div>
      <div class="report-actions"><${Button} type="submit" disabled=${saving}>${saving ? 'در حال ذخیره…' : 'ذخیره سیاست آموزشی'}</${Button}><${Button} type="button" variant="outline" disabled=${saving || !schoolId || !yearId} onClick=${async () => { try { await reportApi.recalculateAnnual({ school: schoolId, academic_year: yearId }); notify({ kind: 'success', message: 'نتایج سالانه و رتبه‌های کلاس، پایه و مدرسه دوباره محاسبه شد.' }); await reload(); } catch (error) { notify({ kind: 'error', message: error.message }); } }}>محاسبه مجدد سالانه</${Button}></div>
    </form>
  </${Card}>`;
}

function SummerManager({ workspace, schoolId, yearId, enrollment, reload, notify, canManage }) {
  const programs = workspace.summerPrograms.filter(item => !schoolId || item.school === schoolId);
  const [programId, setProgramId] = useState('');
  const [title, setTitle] = useState('دوره تابستان');
  const [threshold, setThreshold] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [scoreValues, setScoreValues] = useState({});
  const active = programs.find(item => item.id === programId) ?? programs[0];
  const programCourses = workspace.summerCourses.filter(item => item.program === active?.id);
  const registrations = workspace.summerRegistrations.filter(item => item.program === active?.id);
  const activeRegistration = registrations.find(item => item.enrollment === enrollment?.id);
  const courseRegistrations = workspace.summerCourseRegistrations.filter(item => item.registration === activeRegistration?.id);
  const exam = workspace.summerExams.find(item => item.program === active?.id);
  const scores = workspace.summerScores.filter(item => item.exam === exam?.id);

  useEffect(() => { if (active) setThreshold(active.pass_threshold == null ? '' : String(active.pass_threshold)); }, [active?.id, active?.pass_threshold]);
  const execute = async (work, success) => {
    try { await work(); notify({ kind: 'success', message: success }); await reload(); }
    catch (error) { notify({ kind: 'error', message: error.message }); }
  };
  const createProgram = () => execute(() => reportApi.createSummerProgram({ school: schoolId, academic_year: yearId, title, pass_threshold: normalizeSummerThreshold(threshold) }), 'دوره تابستان با موفقیت ایجاد شد.');
  const updateThreshold = () => execute(() => reportApi.updateSummerProgram(active.id, { pass_threshold: normalizeSummerThreshold(threshold), threshold_change_reason: 'تغییر سیاست حد نصاب دوره تابستان توسط مسئول آموزشی' }), 'حد نصاب اختیاری تابستان با ثبت تاریخچه به‌روزرسانی شد.');
  const enroll = () => execute(() => reportApi.createSummerRegistration({ program: active.id, enrollment: enrollment.id }), 'دانش‌آموز در دوره تابستان ثبت‌نام شد.');
  const addCourse = () => execute(async () => {
    let course = programCourses.find(item => item.subject === subjectId);
    if (!course && !canManage) throw new Error('تعریف درس جدید تابستان فقط در اختیار مدیر یا معاون آموزشی است.');
    if (!course) course = await reportApi.createSummerCourse({ program: active.id, subject: subjectId });
    if (activeRegistration) await reportApi.createSummerCourseRegistration({ registration: activeRegistration.id, course: course.id });
  }, 'درس تابستانی ثبت شد.');
  const createExam = () => execute(() => reportApi.createSummerExam({ program: active.id, title: 'آزمون جامع تابستان', exam_date: new Date().toISOString().slice(0, 10) }), 'آزمون جامع تابستان ایجاد شد.');
  const finalizeExam = () => execute(() => reportApi.finalizeSummerExam(exam.id), 'آزمون جامع پس از کنترل کامل‌بودن تمام نمرات نهایی شد.');
  const saveScore = registration => execute(() => {
    const existing = scores.find(item => item.course_registration === registration.id);
    const body = { exam: exam.id, course_registration: registration.id, value: String(scoreValues[registration.id] ?? existing?.value ?? '') };
    return existing ? reportApi.updateSummerScore(existing.id, { value: body.value }) : reportApi.createSummerScore(body);
  }, 'نمره مستقیم درس ثبت شد.');

  return html`<${Card} className="report-card" title="دوره مستقل تابستان و آزمون جامع" subtitle="برای هر درس فقط نمره مستقیم بین ۰ تا ۲۰ ذخیره می‌شود؛ پاسخ‌نامه و جزئیات سؤال ثبت نخواهد شد.">
    <div class="report-grid report-grid--three">
      <${Field} label="دوره تابستان"><select value=${active?.id ?? ''} onChange=${event => setProgramId(event.currentTarget.value)}><option value="">دوره جدید</option>${programs.map(item => html`<option key=${item.id} value=${item.id}>${item.title}</option>`)}</select></${Field}>
      <${Field} label="عنوان دوره"><input value=${title} onInput=${event => setTitle(event.currentTarget.value)} disabled=${!canManage}/></${Field}>
      <${Field} label="حد نصاب اختیاری" hint="خالی = عدم نمایش هرگونه وضعیت قبولی"><input inputmode="decimal" value=${threshold} onInput=${event => setThreshold(event.currentTarget.value)} placeholder="بدون حد نصاب" disabled=${!canManage}/></${Field}>
    </div>
    <div class="report-actions">${canManage && html`<${Button} onClick=${createProgram} disabled=${!schoolId || !yearId}>ایجاد دوره</${Button}>`}${active && canManage && html`<${Button} variant="outline" onClick=${updateThreshold}>ذخیره حد نصاب</${Button}>`}${active && enrollment && !activeRegistration && html`<${Button} variant="outline" onClick=${enroll}>ثبت‌نام ${enrollment.student_name}</${Button}>`}</div>
    ${active && activeRegistration && html`<div class="report-grid report-grid--three report-summer-courses"><${Field} label="افزودن درس تابستان"><select value=${subjectId} onChange=${event => setSubjectId(event.currentTarget.value)}><option value="">انتخاب درس</option>${workspace.subjects.filter(item => canManage || programCourses.some(course => course.subject === item.id)).map(item => html`<option key=${item.id} value=${item.id}>${item.title}</option>`)}</select></${Field}><div class="report-actions"><${Button} variant="outline" onClick=${addCourse} disabled=${!subjectId}>ثبت درس</${Button}>${!exam && canManage && html`<${Button} variant="outline" onClick=${createExam}>ایجاد آزمون جامع</${Button}>`}${exam?.status === 'draft' && canManage && html`<${Button} variant="outline" onClick=${finalizeExam}>نهایی‌کردن آزمون جامع</${Button}>`}</div></div>`}
    ${activeRegistration && html`<div class="table-scroll"><table class="data-table"><thead><tr><th>درس تابستان</th><th>نمره مستقیم</th>${active.pass_threshold != null && html`<th>وضعیت</th>`}<th>عملیات</th></tr></thead><tbody>${courseRegistrations.map(registration => {
      const course = programCourses.find(item => item.id === registration.course);
      const score = scores.find(item => item.course_registration === registration.id);
      const value = scoreValues[registration.id] ?? score?.value ?? '';
      return html`<tr key=${registration.id}><td>${course?.subject_title ?? registration.subject_title ?? 'درس ثبت‌شده'}</td><td><input class="report-score-input" inputmode="decimal" value=${value} onInput=${event => setScoreValues(previous => ({ ...previous, [registration.id]: event.currentTarget.value }))} placeholder="۰ تا ۲۰" disabled=${exam?.status === 'finalized'}/></td>${active.pass_threshold != null && html`<td>${score?.value == null ? '—' : Number(score.value) >= Number(active.pass_threshold) ? 'قبول' : 'پایین‌تر از حد نصاب'}</td>`}<td><${Button} variant="outline" disabled=${!exam || exam.status === 'finalized'} onClick=${() => saveScore(registration)}>ذخیره نمره</${Button}></td></tr>`;
    })}</tbody></table>${courseRegistrations.length === 0 && html`<p class="report-empty-row">هنوز درسی برای دانش‌آموز انتخاب نشده است.</p>`}</div>`}
  </${Card}>`;
}

function ArchiveTable({ drafts, archives, perform, preview, download }) {
  const statusLabels = { draft: 'پیش‌نویس', submitted: 'منتظر تأیید', approved: 'تأییدشده', rejected: 'بازگشت داده‌شده', rendered: 'صادرشده', completed: 'تکمیل‌شده' };
  return html`<${Card} className="report-card" title="تأیید انسانی و بایگانی نسخه‌ها" subtitle="شماره رهگیری و نسخه فقط بعد از صدور موفق PDF بایگانی‌شده معتبر است.">
    ${drafts.length || archives.length ? html`<div class="table-scroll"><table class="data-table"><thead><tr><th>قالب / بازه</th><th>وضعیت</th><th>رهگیری</th><th>نسخه</th><th>عملیات</th></tr></thead><tbody>
      ${drafts.map(item => html`<tr key=${`draft-${item.id}`}><td>${REPORT_CARD_TEMPLATES.find(layout => layout.key === item.layout_key)?.label ?? item.period_label ?? 'پیش‌نویس کارنامه'}</td><td><${Badge} tone=${item.status === 'approved' ? 'success' : 'info'}>${statusLabels[item.status] ?? item.status}</${Badge}></td><td>${item.tracking_code ?? '—'}</td><td>${item.report_version ?? '—'}</td><td><div class="report-actions"><${Button} variant="outline" onClick=${() => preview(item)}>پیش‌نمایش واقعی</${Button}>${item.status === 'draft' && html`<${Button} variant="outline" onClick=${() => perform(item.id, 'submit')}>ارسال برای تأیید</${Button}>`}${item.status === 'submitted' && hasRole(managers) && html`<${Button} variant="outline" onClick=${() => perform(item.id, 'approve')}>تأیید انسانی</${Button}>`}${item.status === 'approved' && hasRole(managers) && html`<${Button} onClick=${() => perform(item.id, 'render')}>صدور PDF و Word</${Button}>`}</div></td></tr>`)}
      ${archives.map(item => html`<tr key=${`archive-${item.id}`}><td>${item.period_label ?? date(item.created_at)}</td><td><${Badge} tone="success">${statusLabels[item.status] ?? item.status}</${Badge}></td><td>${item.tracking_code ?? '—'}</td><td>${item.report_version ?? '—'}</td><td>${item.download_url ? html`<div class="report-actions"><button class="report-download" onClick=${() => download(item, item.output_format === 'docx' ? 'legacy-docx' : 'pdf')}>دانلود ${item.output_format?.toUpperCase() ?? 'PDF'}</button>${item.editable_download_url && html`<button class="report-download" onClick=${() => download(item, 'docx')}>Word قابل ویرایش</button>`}</div>` : 'در انتظار آماده‌سازی'}</td></tr>`)}
    </tbody></table></div>` : html`<${EmptyState} title="هنوز کارنامه‌ای صادر نشده است" description="ابتدا دانش‌آموز و یکی از هفت قالب واقعی را انتخاب کنید."/>`}
  </${Card}>`;
}

export function ReportsPage({ initialTab = 'reports' }) {
  const { scope, user } = useStore(state => ({ scope: state.scope, user: state.user }));
  const [yearId, setYearId] = useState('');
  const [enrollmentId, setEnrollmentId] = useState('');
  const [templateKey, setTemplateKey] = useState('final_annual');
  const [termId, setTermId] = useState('');
  const [summerRegistrationId, setSummerRegistrationId] = useState('');
  const [tab, setTab] = useState(initialTab);
  const [notice, setNotice] = useState(null);
  const [previewDocument, setPreviewDocument] = useState(null);
  const [busy, setBusy] = useState(false);
  const workspace = useWorkspace(yearId, scope.schoolId);
  const data = workspace.data;
  const enrollment = useMemo(() => data?.enrollments.find(item => item.id === enrollmentId) ?? data?.enrollments[0], [data, enrollmentId]);
  const activeYearId = yearId || enrollment?.academic_year || data?.academicYears[0]?.id;
  const schoolId = scope.schoolId || enrollment?.school;
  const layout = reportTemplateByKey(templateKey);
  const activeSettings = data?.settings.find(item => item.school === schoolId && item.academic_year === activeYearId);
  const compatibleTerms = data?.terms.filter(item => item.academic_year === activeYearId && item.code === layout.period) ?? [];
  const registration = data?.summerRegistrations.find(item => item.id === summerRegistrationId)
    ?? data?.summerRegistrations.find(item => item.enrollment === enrollment?.id);
  const manager = hasRole(managers);
  const summerDataEntry = manager || hasRole(['operator']);

  if (workspace.status === 'loading') return html`<div class="page"><${Skeleton} lines=${10}/></div>`;
  if (workspace.status === 'error') return html`<div class="page"><${ErrorState} error=${workspace.error} onRetry=${workspace.reload}/></div>`;

  const run = async action => {
    setBusy(true);
    try { await action(); await workspace.reload(); }
    catch (error) { setNotice({ kind: 'error', message: error.message }); }
    finally { setBusy(false); }
  };
  const createDraft = () => run(async () => {
    let template = data.templates.find(item => item.layout_key === templateKey && (!item.school || item.school === schoolId));
    if (!template) {
      if (!manager) throw new Error('این قالب هنوز آماده نشده است؛ مدیر یا معاون آموزشی باید آن را برای مدرسه فعال کند.');
      const organization = selectedOrganization(user, schoolId) || scope.organizationId
        || data.academicYears.find(item => item.id === activeYearId)?.organization;
      if (!organization || !schoolId) throw new Error('برای ساخت قالب، مدرسه و مجموعه فعال را مشخص کنید.');
      template = await reportApi.createTemplate(buildReportTemplatePayload({ organization, school: schoolId, templateKey }));
    }
    const payload = buildReportDraftPayload({
      templateId: template.id, enrollmentId: enrollment?.id, templateKey,
      termId: termId || compatibleTerms[0]?.id, summerRegistrationId: registration?.id,
    });
    await reportApi.createDraft(payload);
    setNotice({ kind: 'success', message: 'پیش‌نویس واقعی ساخته شد؛ برای صدور رسمی باید ارسال، تأیید انسانی و اعتبارسنجی انجام شود.' });
  });
  const transition = (id, action) => run(async () => {
    await reportApi.transitionDraft(id, action);
    setNotice({ kind: 'success', message: action === 'render' ? 'فرایند صدور نسخه بایگانی‌شده آغاز شد.' : 'وضعیت پیش‌نویس با موفقیت تغییر کرد.' });
  });
  const previewDraft = draft => run(async () => {
    const result = await reportApi.previewDraft(draft.id);
    setPreviewDocument({ title: draft.period_label ?? 'پیش‌نمایش کارنامه', html: result.html, warnings: result.warnings ?? [] });
  });
  const download = (archive, format) => run(async () => {
    const content = await reportApi.downloadArchive(archive.id, format);
    const objectUrl = URL.createObjectURL(content);
    const element = document.createElement('a');
    element.href = objectUrl;
    element.download = `${archive.tracking_code ?? archive.id}.${format === 'legacy-docx' ? 'docx' : format}`;
    element.click();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  });

  return html`<div class="page page--reports" dir="rtl">
    <${PageHeader} eyebrow="گزارش‌های آموزشی و سیاست تحصیلی" title="مرکز کارنامه‌های رسمی، تحلیلی و تابستان" subtitle="هفت قالب مستقل، نسخه‌بندی تغییرناپذیر و تأیید انسانی قبل از صدور"/>
    <${Notice} notice=${notice}/>
    <nav class="report-tabs" aria-label="بخش‌های مرکز کارنامه"><button class=${tab === 'reports' ? 'is-active' : ''} onClick=${() => setTab('reports')}>کارنامه و بایگانی</button>${manager && html`<button class=${tab === 'settings' ? 'is-active' : ''} onClick=${() => setTab('settings')}>وزن نوبت‌ها و رتبه‌ها</button>`}${summerDataEntry && html`<button class=${tab === 'summer' ? 'is-active' : ''} onClick=${() => setTab('summer')}>دوره تابستان</button>`}</nav>
    <${Card} className="report-card" title="انتخاب دانش‌آموز و سال تحصیلی"><div class="report-grid report-grid--three">
      <${Field} label="سال تحصیلی"><select value=${activeYearId ?? ''} onChange=${event => setYearId(event.currentTarget.value)}>${data.academicYears.map(item => html`<option key=${item.id} value=${item.id}>${item.title}</option>`)}</select></${Field}>
      <${Field} label="دانش‌آموز"><select value=${enrollment?.id ?? ''} onChange=${event => setEnrollmentId(event.currentTarget.value)}><option value="">انتخاب دانش‌آموز</option>${data.enrollments.map(item => html`<option key=${item.id} value=${item.id}>${item.student_name} · ${item.grade_title} · ${item.class_title}</option>`)}</select></${Field}>
      <${Field} label="مدرسه فعال"><input value=${enrollment?.school_name ?? 'مدرسه انتخاب نشده است'} readonly/></${Field}>
    </div></${Card}>
    ${tab === 'reports' && html`<${Card} className="report-card" title="هفت قالب مستقل کارنامه" subtitle="تحلیلی A3 افقی و کارنامه رسمی/تابستان A4 عمودی؛ همه خروجی‌ها از snapshot معتبر تولید می‌شوند.">
      <div class="report-layout-grid">${REPORT_CARD_TEMPLATES.map(item => html`<button key=${item.key} class=${`report-layout ${templateKey === item.key ? 'is-selected' : ''}`} onClick=${() => { setTemplateKey(item.key); setTermId(''); }}><strong>${item.label}</strong><small>${item.pageSize}</small></button>`)}</div>
      <div class="report-grid report-grid--three">${['first', 'second'].includes(layout.period) && html`<${Field} label="نوبت تحصیلی"><select value=${termId || compatibleTerms[0]?.id || ''} onChange=${event => setTermId(event.currentTarget.value)}><option value="">انتخاب نوبت</option>${compatibleTerms.map(item => html`<option key=${item.id} value=${item.id}>${item.title}</option>`)}</select></${Field}>`}${layout.family === 'summer' && html`<${Field} label="ثبت‌نام تابستان دانش‌آموز"><select value=${registration?.id ?? ''} onChange=${event => setSummerRegistrationId(event.currentTarget.value)}><option value="">انتخاب ثبت‌نام تابستان</option>${data.summerRegistrations.filter(item => item.enrollment === enrollment?.id).map(item => html`<option key=${item.id} value=${item.id}>${data.summerPrograms.find(program => program.id === item.program)?.title ?? 'دوره تابستان'}</option>`)}</select></${Field}>`}</div>
      <div class="report-actions"><${Button} onClick=${createDraft} disabled=${busy || !enrollment || (layout.family === 'summer' && !registration)}>${busy ? 'در حال پردازش…' : 'ساخت پیش‌نویس و آماده‌سازی تأیید'}</${Button}></div>
    </${Card}><${ArchiveTable} drafts=${data.drafts} archives=${data.archives} perform=${transition} preview=${previewDraft} download=${download}/>${previewDocument && html`<${Card} className="report-card" title=${`پیش‌نمایش واقعی: ${previewDocument.title}`} subtitle="پیش‌نمایش حتی با اطلاعات ناقص قابل مشاهده است؛ صدور رسمی همچنان نیازمند تأیید و تکمیل داده‌هاست."><div class="report-actions"><${Button} variant="outline" onClick=${() => setPreviewDocument(null)}>بستن پیش‌نمایش</${Button}></div>${previewDocument.warnings.map((warning, index) => html`<p key=${index} class="report-notice report-notice--error">${warning}</p>`)}<iframe class="report-preview-frame" title="پیش‌نمایش امن کارنامه" sandbox="" srcDoc=${previewDocument.html}></iframe></${Card}>`}`}
    ${tab === 'settings' && manager && html`<${AcademicSettings} current=${activeSettings} schoolId=${schoolId} yearId=${activeYearId} reload=${workspace.reload} notify=${setNotice}/>`}
    ${tab === 'summer' && summerDataEntry && html`<${SummerManager} workspace=${data} schoolId=${schoolId} yearId=${activeYearId} enrollment=${enrollment} reload=${workspace.reload} notify=${setNotice} canManage=${manager}/>`}
  </div>`;
}
