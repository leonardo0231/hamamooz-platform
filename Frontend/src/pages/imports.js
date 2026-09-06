import { html, useCallback, useEffect, useMemo, useRef, useState } from '../core/view.js';
import { apiRequest, downloadBlob } from '../core/api.js';
import { config } from '../core/config.js';
import {
  COMPREHENSIVE_IMPORT_TYPE,
  canCancelImport,
  canRetryImport,
  importFileName,
  importStatusLabel,
  importStatusTone,
  importSummaryEntries,
  isImportInProgress,
  validateComprehensiveImportFile,
} from '../core/imports.js';
import { useStore } from '../core/store.js';
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, Progress, Skeleton, StatCard } from '../components/ui.js';
import { Icon } from '../components/icons.js';

const IMPORT_TEMPLATE_PATH = `imports/templates/${COMPREHENSIVE_IMPORT_TYPE}/`;
const IMPORT_POLL_INTERVAL_MS = 5_000;
const fa = value => new Intl.NumberFormat('fa-IR').format(Number(value) || 0);
const dateTime = value => value ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '—';
const results = value => Array.isArray(value) ? value : value?.results ?? [];

const summaryLabels = {
  classes_created: 'کلاس جدید', classes_updated: 'کلاس به‌روزشده', classes_unchanged: 'کلاس بدون تغییر',
  students_created: 'دانش‌آموز جدید', students_updated: 'دانش‌آموز به‌روزشده', students_unchanged: 'دانش‌آموز بدون تغییر',
  enrollments_created: 'ثبت‌نام جدید', enrollments_updated: 'ثبت‌نام به‌روزشده', enrollments_unchanged: 'ثبت‌نام بدون تغییر',
  evaluations_created: 'ارزیابی جدید', evaluations_updated: 'ارزیابی به‌روزشده', evaluations_unchanged: 'ارزیابی بدون تغییر',
  metric_scores_created: 'شاخص جدید', metric_scores_updated: 'شاخص به‌روزشده', metric_scores_unchanged: 'شاخص بدون تغییر',
  records_deleted: 'رکورد حذف‌شده',
};

const demoSchools = [{ id: 'demo-school', name: 'دبیرستان نمونهٔ هم‌آموز' }];
const demoJobs = [{
  id: 'demo-import-completed', school: 'demo-school', school_name: 'دبیرستان نمونهٔ هم‌آموز',
  import_type: COMPREHENSIVE_IMPORT_TYPE, status: 'completed', total_rows: 128, successful_rows: 128,
  error_count: 0, source_file: '/media/imports/demo-comprehensive-school.xlsx',
  result_summary: { classes_created: 4, students_created: 38, enrollments_created: 38, evaluations_created: 86 },
  created_at: '2026-08-31T10:00:00Z', finished_at: '2026-08-31T10:01:18Z',
}];

function schoolName(item) {
  return item?.official_name || item?.name || item?.title || item?.code || 'مدرسه';
}

function sourceError(job) {
  const first = Array.isArray(job?.errors) ? job.errors[0] : null;
  return first?.message || job?.error_message || null;
}

function ImportSummary({ summary }) {
  const entries = importSummaryEntries(summary);
  if (!entries.length) return null;
  return html`<dl class="import-job__summary">${entries.slice(0, 6).map(([key, value]) => html`<div key=${key}><dt>${summaryLabels[key] ?? key.replaceAll('_', ' ')}</dt><dd>${typeof value === 'number' ? fa(value) : value === true ? 'بله' : value === false ? 'خیر' : value}</dd></div>`)}</dl>`;
}

function ImportJob({ job, actionKey, onRetry, onCancel, onDownloadErrors }) {
  const progress = job.total_rows ? Math.round((Number(job.successful_rows) / Number(job.total_rows)) * 100) : isImportInProgress(job) ? 12 : job.status === 'completed' ? 100 : 0;
  const busy = actionKey?.endsWith(`:${job.id}`);
  const error = sourceError(job);
  return html`<article class="import-job">
    <header class="import-job__header">
      <div><strong>${job.school_name || 'مدرسهٔ انتخاب‌شده'}</strong><small>${importFileName(job)} · ${dateTime(job.created_at)}</small></div>
      <${Badge} tone=${importStatusTone(job.status)}>${importStatusLabel(job.status)}</${Badge}>
    </header>
    <div class="import-job__counts"><span><b>${fa(job.successful_rows)}</b> موفق</span><span><b>${fa(job.total_rows)}</b> سطر</span><span class=${Number(job.error_count) ? 'is-error' : ''}><b>${fa(job.error_count)}</b> خطا</span></div>
    <${Progress} value=${progress} label=${`پیشرفت ورود ${importFileName(job)}`}/>
    <${ImportSummary} summary=${job.result_summary}/>
    ${error && html`<p class="import-job__error" role="alert">${error}</p>`}
    <footer class="import-job__actions">
      ${Number(job.error_count) > 0 && html`<${Button} type="button" variant="outline" icon="download" disabled=${busy} onClick=${() => onDownloadErrors(job)}>دانلود خطاها</${Button}>`}
      ${canRetryImport(job) && html`<${Button} type="button" variant="outline" icon="upload" disabled=${busy} onClick=${() => onRetry(job)}>تلاش دوباره</${Button}>`}
      ${canCancelImport(job) && html`<${Button} type="button" variant="outline" icon="close" disabled=${busy} onClick=${() => onCancel(job)}>لغو ورود</${Button}>`}
      ${job.finished_at && html`<small>پایان: ${dateTime(job.finished_at)}</small>`}
    </footer>
  </article>`;
}

export function ImportsPage() {
  const scope = useStore(state => state.scope);
  const DEFAULT_SCHOOL_NAME = "مدرسه بعثت";
  const [catalogError, setCatalogError] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState(null);
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [notice, setNotice] = useState('');
  const [uploading, setUploading] = useState(false);
  const [actionKey, setActionKey] = useState('');
  const inputRef = useRef(null);


  const loadJobs = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setJobsLoading(true);
    if (config.demoMode) {
      setJobs(demoJobs);
      setJobsError(null);
      if (!silent) setJobsLoading(false);
      return;
    }
    try {
      const response = await apiRequest('imports/', {
        query: { page_size: 50, import_type: COMPREHENSIVE_IMPORT_TYPE, ...(selectedSchool ? { school: selectedSchool } : {}) },
      });
      const listed = results(response).sort((left, right) => new Date(right.created_at ?? 0) - new Date(left.created_at ?? 0));
      setJobs(listed);
      setJobsError(null);
    } catch (error) {
      setJobsError(error);
    } finally {
      if (!silent) setJobsLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => { void loadSchools(); }, [loadSchools]);

  const hasActiveJob = jobs.some(isImportInProgress);
  useEffect(() => {
    if (config.demoMode || !hasActiveJob) return undefined;
    const timer = window.setInterval(() => { void loadJobs({ silent: true }); }, IMPORT_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [hasActiveJob, loadJobs]);

  const totals = useMemo(() => jobs.reduce((result, job) => ({
    total: result.total + 1,
    active: result.active + (isImportInProgress(job) ? 1 : 0),
    completed: result.completed + (job.status === 'completed' ? 1 : 0),
    errors: result.errors + Number(job.error_count || 0),
  }), { total: 0, active: 0, completed: 0, errors: 0 }), [jobs]);

  const clearFile = () => {
    setFile(null);
    setFileError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const selectFile = event => {
    const nextFile = event.currentTarget.files?.[0] ?? null;
    setFile(nextFile);
    setFileError(validateComprehensiveImportFile(nextFile));
    setSubmitError(null);
    setNotice('');
  };

  const downloadTemplate = async () => {
    if (config.demoMode) {
      setNotice('در حالت نمایشی، دانلود قالب به سرویس متصل انجام نمی‌شود.');
      return;
    }
    setActionKey('template');
    setSubmitError(null);
    try {
      const blob = await apiRequest(IMPORT_TEMPLATE_PATH, { responseType: 'blob' });
      downloadBlob(blob, 'comprehensive_school_template.xlsx');
      setNotice('قالب جامع مدرسه دانلود شد.');
    } catch (error) {
      setSubmitError(error);
    } finally {
      setActionKey('');
    }
  };

  const submit = async event => {
    event.preventDefault();
    const validationError = validateComprehensiveImportFile(file);
    if (validationError) {
      setFileError(validationError);
      return;
    }
    setUploading(true);
    setSubmitError(null);
    setNotice('');
    try {
      if (config.demoMode) {
        const school = schools.find(item => String(item.id) === String(selectedSchool));
        const demoJob = {
          ...demoJobs[0], id: `demo-import-${Date.now()}`, school: selectedSchool, school_name: schoolName(school),
          source_file: `/media/imports/${file.name}`, created_at: new Date().toISOString(), finished_at: new Date().toISOString(),
        };
        setJobs(current => [demoJob, ...current.filter(item => item.id !== demoJob.id)]);
        clearFile();
        setNotice('ورود نمونه با موفقیت شبیه‌سازی شد؛ در محیط متصل Job واقعی ایجاد می‌شود.');
        return;
      }
      const body = new FormData();
      body.set('import_type', COMPREHENSIVE_IMPORT_TYPE);
      body.set('source_file', file, file.name);
      const job = await apiRequest('imports/', { method: 'POST', body });
      setJobs(current => [job, ...current.filter(item => String(item.id) !== String(job.id))]);
      clearFile();
      setNotice('فایل ثبت شد و اعتبارسنجی/ورود آن در پس‌زمینه شروع شد.');
    } catch (error) {
      setSubmitError(error);
    } finally {
      setUploading(false);
    }
  };

  const updateJob = job => setJobs(current => current.map(item => String(item.id) === String(job.id) ? job : item));

  const retry = async job => {
    setActionKey(`retry:${job.id}`);
    setSubmitError(null);
    try {
      const next = await apiRequest(`imports/${job.id}/retry/`, { method: 'POST' });
      updateJob(next);
      setNotice('Job دوباره در صف پردازش قرار گرفت.');
    } catch (error) {
      setSubmitError(error);
    } finally {
      setActionKey('');
    }
  };

  const cancel = async job => {
    setActionKey(`cancel:${job.id}`);
    setSubmitError(null);
    try {
      const next = await apiRequest(`imports/${job.id}/cancel/`, { method: 'POST' });
      updateJob(next);
      setNotice('درخواست لغو ثبت شد.');
    } catch (error) {
      setSubmitError(error);
    } finally {
      setActionKey('');
    }
  };

  const downloadErrors = async job => {
    setActionKey(`errors:${job.id}`);
    setSubmitError(null);
    try {
      const blob = await apiRequest(`imports/${job.id}/errors/`, { responseType: 'blob' });
      downloadBlob(blob, `import-errors-${job.id}.xlsx`);
      setNotice('فایل خطاهای ورود دانلود شد.');
    } catch (error) {
      setSubmitError(error);
    } finally {
      setActionKey('');
    }
  };

  return html`<div class="page import-workspace">
    <${PageHeader}
      eyebrow="ورود داده‌های مدرسه"
      title="ورود فایل جامع Excel"
      subtitle="قالب رسمی را دانلود کنید، فایل کامل مدرسه را ارسال کنید و نتیجهٔ اعتبارسنجی و ورود را در همین صفحه پیگیری کنید."
      actions=${html`<${Button} type="button" variant="outline" icon="download" disabled=${actionKey === 'template'} onClick=${downloadTemplate}>${actionKey === 'template' ? 'در حال دانلود…' : 'دانلود قالب جامع'}</${Button}>`}
    />
    <section class="stats-grid import-stats"><${StatCard} label="Jobهای ورود" value=${fa(totals.total)} icon="folder" tone="purple"/><${StatCard} label="در صف یا پردازش" value=${fa(totals.active)} icon="upload" tone="orange"/><${StatCard} label="تکمیل‌شده" value=${fa(totals.completed)} icon="check" tone="green"/><${StatCard} label="خطاهای ثبت‌شده" value=${fa(totals.errors)} icon="alert" tone="pink"/></section>

    <section class="import-layout">
      <${Card} className="import-upload-card" title="ارسال فایل جامع مدرسه" subtitle="فقط Excel با پسوند XLSX و حداکثر حجم ۱۰ مگابایت پذیرفته می‌شود." icon="upload">
        <form class="import-upload-form" onSubmit=${submit}>
          <label class="import-field">مدرسهٔ مقصد<select value=${selectedSchool} disabled=${catalogLoading || !schools.length} onInput=${event => setSelectedSchool(event.currentTarget.value)}>
            <option value="">${catalogLoading ? 'در حال دریافت مدرسه‌ها…' : 'انتخاب مدرسه'}</option>
            ${schools.map(school => html`<option value=${school.id} key=${school.id}>${schoolName(school)}</option>`)}
          </select></label>
          ${catalogError && html`<p class="import-inline-error" role="alert">${catalogError.message}</p>`}
          <label class=${`import-file-picker ${fileError ? 'is-invalid' : ''}`}>
            <input ref=${inputRef} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange=${selectFile} aria-describedby="import-file-help import-file-error" />
            <span class="import-file-picker__icon"><${Icon} name="upload" size=${27}/></span>
            <span class="import-file-picker__content"><strong>${file ? file.name : 'انتخاب فایل جامع مدرسه'}</strong><small id="import-file-help">سه Sheet ورودی: کلاس‌بندی، دانش‌آموزان و ثبت اطلاعات</small>${file && html`<em>${fa(file.size / 1024)} کیلوبایت</em>`}</span>
          </label>
          ${fileError && html`<p id="import-file-error" class="import-inline-error" role="alert">${fileError}</p>`}
          <div class="import-upload-form__actions">${file && html`<${Button} type="button" variant="outline" onClick=${clearFile}>حذف فایل</${Button}>`}<${Button} icon="upload" disabled=${uploading || Boolean(fileError) || !file || !selectedSchool}>${uploading ? 'در حال ثبت…' : 'ثبت و شروع ورود'}</${Button}></div>
        </form>
        <aside class="import-upload-card__guide"><strong>قبل از ارسال</strong><ul><li>از آخرین قالب دانلودشده استفاده کنید.</li><li>کد ملی را در Excel به‌صورت Text نگه دارید تا صفرهای ابتدا حذف نشود.</li><li>وجود خطا باعث ثبت ناقص نمی‌شود؛ ابتدا همهٔ داده‌ها اعتبارسنجی می‌شوند.</li></ul></aside>
      </${Card}>
      <${Card} className="import-process-card" title="مسیر امن ورود اطلاعات" subtitle="پردازش فایل در سرور انجام می‌شود تا منطق Excel و اطلاعات رسمی یک‌جا کنترل شود." icon="shield">
        <ol class="import-process"><li><span>۱</span><div><strong>دانلود قالب</strong><p>ساختار Sheetها و ستون‌های استاندارد را دریافت کنید.</p></div></li><li><span>۲</span><div><strong>بارگذاری و اعتبارسنجی</strong><p>قالب، کدها و اتصال دانش‌آموز به کلاس پیش از ثبت بررسی می‌شود.</p></div></li><li><span>۳</span><div><strong>ورود اتمیک و نتیجه</strong><p>در پایان شمارنده‌ها، خطاها و امکان تکرار Job در دسترس است.</p></div></li></ol>
      </${Card}>
    </section>

    ${(notice || submitError) && html`<div class=${`import-feedback ${submitError ? 'import-feedback--error' : ''}`} role=${submitError ? 'alert' : 'status'} aria-live="polite">${submitError?.message ?? notice}</div>`}

    <${Card} title="Jobهای ورود اطلاعات" subtitle="Jobهای در صف و در حال پردازش هر ۵ ثانیه خودکار به‌روزرسانی می‌شوند." action=${html`<${Button} type="button" variant="outline" disabled=${jobsLoading} onClick=${() => void loadJobs()}>به‌روزرسانی</${Button}>`}>
      ${jobsLoading ? html`<${Skeleton} lines=${4}/>` : jobsError ? html`<${ErrorState} error=${jobsError} onRetry=${() => void loadJobs()}/>` : jobs.length ? html`<div class="import-jobs">${jobs.map(job => html`<${ImportJob} key=${job.id} job=${job} actionKey=${actionKey} onRetry=${retry} onCancel=${cancel} onDownloadErrors=${downloadErrors}/>`)} </div>` : html`<${EmptyState} title="هنوز فایلی برای ورود ثبت نشده است" description="قالب جامع را دانلود کنید، آن را کامل کنید و از همین صفحه ارسال کنید." icon="upload"/>`}
    </${Card}>
  </div>`;
}
