import { html, useEffect, useMemo, useState } from '../core/view.js';
import { apiRequest, downloadBlob } from '../core/api.js';
import { AnalyticalReport } from '../components/analytical-report.js';
import { Badge, Button, Card, ErrorState, PageHeader, Progress, Skeleton, StatCard } from '../components/ui.js';

const fa = value => new Intl.NumberFormat('fa-IR').format(Number(value) || 0);
const list = value => Array.isArray(value) ? value : value?.results ?? [];
const isWorking = batch => ['queued', 'processing'].includes(batch.status);
const entityLabel = item => item?.official_name || item?.name || item?.title || item?.code || item?.id || '—';
const pageSizeLabel = pageSize => ({
  digital_3x2: 'دیجیتال ۳:۲ · مطابق نمونهٔ کارنامه',
  a3_landscape: 'A3 افقی · داشبورد جامع',
  a4_portrait: 'A4 عمودی · نسخهٔ خوانا',
})[pageSize] ?? 'خروجی PDF';

function ScopeSelect({ value, onChange }) {
  return html`<label>دامنهٔ تولید<select value=${value} onInput=${event => onChange(event.currentTarget.value)}>
    <option value="class">یک کلاس</option><option value="school">کل مدرسه</option>
  </select></label>`;
}

function Field({ label, value, onChange, options = [], placeholder, disabled = false, required = false }) {
  if (!options.length) {
    return html`<label>${label}<input required=${required} disabled=${disabled} value=${value} placeholder=${placeholder} onInput=${event => onChange(event.currentTarget.value)}/></label>`;
  }
  return html`<label>${label}<select required=${required} disabled=${disabled} value=${value} onInput=${event => onChange(event.currentTarget.value)}>
    <option value="">${placeholder ?? `انتخاب ${label}`}</option>${options.map(item => html`<option value=${item.id}>${entityLabel(item)}</option>`)}
  </select></label>`;
}

function statusTone(status) {
  if (status === 'completed') return 'success';
  if (status === 'partial') return 'important';
  if (status === 'failed') return 'danger';
  return 'info';
}

function statusLabel(status) {
  return ({ queued: 'در صف', processing: 'در حال تولید', completed: 'تکمیل‌شده', partial: 'تکمیل با خطا', failed: 'ناموفق' })[status] ?? status;
}

export function ReportsPage() {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [error, setError] = useState(null);
  const [catalog, setCatalog] = useState({ schools: [], years: [], terms: [], classes: [] });
  const [form, setForm] = useState({ school: '', academic_year: '', term: '', class_section: '', scope: 'class', page_size: 'digital_3x2' });
  const [creating, setCreating] = useState(false);
  const [previewSnapshot, setPreviewSnapshot] = useState(null);
  const [previewReportId, setPreviewReportId] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      setBatches(list(await apiRequest('reports/batches/')));
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCatalog = async () => {
    setCatalogLoading(true);
    try {
      const [schools, years, terms, classes] = await Promise.all([
        apiRequest('schools/'), apiRequest('academic-years/'), apiRequest('terms/'), apiRequest('classes/'),
      ]);
      setCatalog({ schools: list(schools), years: list(years), terms: list(terms), classes: list(classes) });
    } catch {
      // The textual UUID fields remain usable for scoped accounts that are not
      // allowed to list these catalogues.
    } finally {
      setCatalogLoading(false);
    }
  };

  const openPreview = async item => {
    const reportId = typeof item === 'string' ? item : item?.report_id;
    if (!reportId) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const archive = await apiRequest(`reports/${reportId}/`);
      setPreviewSnapshot(archive.snapshot);
      setPreviewReportId(archive.id);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setPreviewError(err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const downloadFile = async (key, path, filename) => {
    setDownloading(key);
    setDownloadError(null);
    try {
      downloadBlob(await apiRequest(path, { responseType: 'blob' }), filename);
    } catch (err) {
      setDownloadError(err);
    } finally {
      setDownloading(null);
    }
  };

  useEffect(() => {
    void load();
    void loadCatalog();
    const reportId = new URLSearchParams(window.location.search).get('report');
    if (reportId) void openPreview(reportId);
  }, []);

  const hasRunningBatch = batches.some(isWorking);
  useEffect(() => {
    if (!hasRunningBatch) return undefined;
    const timer = window.setInterval(() => { void load(); }, 6000);
    return () => window.clearInterval(timer);
  }, [hasRunningBatch]);

  useEffect(() => {
    if (form.school || !catalog.schools.length) return;
    setForm(current => ({ ...current, school: String(catalog.schools[0].id) }));
  }, [catalog.schools, form.school]);

  const years = useMemo(() => catalog.years.filter(item => !form.school || !item.organization || String(item.organization) === String(catalog.schools.find(school => String(school.id) === String(form.school))?.organization)), [catalog.years, catalog.schools, form.school]);
  const terms = useMemo(() => catalog.terms.filter(item => !form.academic_year || String(item.academic_year) === String(form.academic_year)), [catalog.terms, form.academic_year]);
  const classes = useMemo(() => catalog.classes.filter(item => (!form.school || String(item.school) === String(form.school)) && (!form.academic_year || String(item.academic_year) === String(form.academic_year))), [catalog.classes, form.school, form.academic_year]);

  const updateForm = (field, value) => {
    setForm(current => ({
      ...current,
      [field]: value,
      ...(field === 'school' ? { class_section: '' } : {}),
      ...(field === 'academic_year' ? { term: '', class_section: '' } : {}),
    }));
  };

  const create = async event => {
    event.preventDefault();
    setCreating(true);
    try {
      const payload = { ...form, class_section: form.scope === 'class' ? form.class_section : null };
      const batch = await apiRequest('reports/batches/', { method: 'POST', body: payload });
      setBatches(current => [batch, ...current]);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setCreating(false);
    }
  };

  const totals = batches.reduce((result, batch) => ({
    total: result.total + batch.total_count,
    done: result.done + batch.completed_count,
    failed: result.failed + batch.failed_count,
  }), { total: 0, done: 0, failed: 0 });

  return html`<div class="page report-workspace">
    <${PageHeader} eyebrow="کارنامه تحلیلی" title="کارنامهٔ رشد؛ مشاهده، تحلیل و خروجی رسمی" subtitle="برای یک کلاس یا کل مدرسه کارنامه‌های رنگی بسازید، وضعیت تولید را ببینید و هر دانش‌آموز را در همان سامانه بررسی کنید."/>
    <section class="stats-grid"><${StatCard} label="بسته‌های گزارش" value=${fa(batches.length)} icon="report" tone="purple"/><${StatCard} label="کارنامه‌های آماده" value=${fa(totals.done)} icon="check" tone="green"/><${StatCard} label="در صف یا تولید" value=${fa(Math.max(0, totals.total - totals.done - totals.failed))} icon="calendar" tone="orange"/><${StatCard} label="نیازمند بررسی" value=${fa(totals.failed)} icon="alert" tone="pink"/></section>

    <section class="report-preview-zone">
      <header class="report-preview-zone__header"><div><span>پیش‌نمایش تعاملی</span><h2>${previewSnapshot ? 'کارنامهٔ انتخاب‌شده' : 'نمونهٔ کارنامهٔ قابل ارائه'}</h2><p>${previewSnapshot ? 'این نمایش از snapshot نهاییِ آرشیوشده ساخته شده است.' : 'همان ساختار در خروجی PDF دیجیتال ۳:۲، A3 و A4 استفاده می‌شود.'}</p></div><div class="report-preview-zone__actions"><div class="report-preview-zone__legend"><i></i>داده‌های آموزشی، رفتاری، حضور و فعالیت‌ها</div>${previewReportId && html`<button class="button button--outline" type="button" disabled=${downloading === `report:${previewReportId}`} onClick=${() => void downloadFile(`report:${previewReportId}`, `reports/${previewReportId}/download/`, 'report-card.pdf')}>${downloading === `report:${previewReportId}` ? 'در حال دریافت…' : 'دریافت PDF'}</button>`}</div></header>
      ${previewError ? html`<${ErrorState} error=${previewError} onRetry=${() => setPreviewError(null)}/>` : html`<${AnalyticalReport} snapshot=${previewSnapshot} loading=${previewLoading}/>`}
    </section>

    <${Card} className="report-create" title="تولید گروهی کارنامه" subtitle="انتخاب‌ها فقط در محدودهٔ دسترسی فعلی شما اعتبارسنجی می‌شوند. برای خروجی رسمی، نمرات همهٔ دروس باید نهایی و قفل شده باشند.">
      <form onSubmit=${create} class="report-create__form">
        <${Field} label="مدرسه" required=${true} value=${form.school} options=${catalog.schools} placeholder=${catalogLoading ? 'در حال دریافت…' : 'انتخاب مدرسه'} onChange=${value => updateForm('school', value)}/>
        <${Field} label="سال تحصیلی" required=${true} value=${form.academic_year} options=${years} placeholder=${catalogLoading ? 'در حال دریافت…' : 'انتخاب سال'} onChange=${value => updateForm('academic_year', value)}/>
        <${Field} label="نوبت" required=${true} value=${form.term} options=${terms} placeholder=${catalogLoading ? 'در حال دریافت…' : 'انتخاب نوبت'} onChange=${value => updateForm('term', value)}/>
        <${ScopeSelect} value=${form.scope} onChange=${value => updateForm('scope', value)}/>
        ${form.scope === 'class' && html`<${Field} label="کلاس" required=${true} value=${form.class_section} options=${classes} placeholder=${catalogLoading ? 'در حال دریافت…' : 'انتخاب کلاس'} onChange=${value => updateForm('class_section', value)}/>`}
        <label>اندازهٔ PDF<select value=${form.page_size} onInput=${event => updateForm('page_size', event.currentTarget.value)}><option value="digital_3x2">دیجیتال ۳:۲ · مطابق نمونهٔ کارنامه</option><option value="a3_landscape">A3 افقی · یک صفحهٔ جامع</option><option value="a4_portrait">A4 عمودی · چندصفحهٔ خوانا</option></select></label>
        <div class="report-create__action"><${Button} icon="report" disabled=${creating}>${creating ? 'در حال ثبت…' : 'شروع تولید گروهی'}</${Button}><small>هر دانش‌آموز یک PDF مستقل و در پایان یک ZIP دریافت می‌کند.</small></div>
      </form>
    </${Card}>

    <${Card} title="بسته‌های تولیدشده" subtitle="خطای یک دانش‌آموز باعث توقف دیگر خروجی‌ها نمی‌شود. با انتخاب هر موردِ آماده، همان کارنامهٔ نهایی در بالا نمایش داده می‌شود." action=${html`<${Button} variant="outline" onClick=${load}>به‌روزرسانی</${Button}>`}>
      ${downloadError && html`<p class="report-download-error" role="alert">${downloadError.message ?? 'دانلود فایل انجام نشد.'}</p>`}
      ${loading ? html`<${Skeleton} lines=${6}/>` : error ? html`<${ErrorState} error=${error} onRetry=${load}/>` : html`<div class="report-batches">${batches.map(batch => html`<article class="report-batch"><header><div><strong>${batch.scope === 'school' ? 'کل مدرسه' : 'کلاس منتخب'}</strong><small>${pageSizeLabel(batch.page_size)}</small></div><${Badge} tone=${statusTone(batch.status)}>${statusLabel(batch.status)}</${Badge}></header><${Progress} value=${batch.progress_percent} label="پیشرفت تولید"/><footer><span>${fa(batch.completed_count)} آماده از ${fa(batch.total_count)} · ${fa(batch.failed_count)} ناموفق</span>${batch.zip_download_url && html`<button class="button button--outline" type="button" disabled=${downloading === `batch:${batch.id}`} onClick=${() => void downloadFile(`batch:${batch.id}`, `reports/batches/${batch.id}/download/`, 'report-cards.zip')}>${downloading === `batch:${batch.id}` ? 'در حال دریافت…' : 'دانلود ZIP'}</button>`}</footer>${batch.items?.length ? html`<div class="report-batch__students">${batch.items.map(item => html`<div><span><b>${item.student_name}</b><small>${item.national_id}</small></span><${Badge} tone=${statusTone(item.status === 'completed' ? 'completed' : item.status === 'failed' ? 'failed' : 'processing')}>${statusLabel(item.status)}</${Badge}>${item.report_id && html`<button class="report-batch__preview" type="button" onClick=${() => void openPreview(item)}>نمایش</button>`}${item.status === 'completed' && item.report_id && html`<button class="report-batch__preview" type="button" onClick=${() => void downloadFile(`report:${item.report_id}`, `reports/${item.report_id}/download/`, 'report-card.pdf')}>PDF</button>`}</div>`)}</div>` : null}</article>`)}${!batches.length && html`<p class="report-empty">هنوز بسته‌ای تولید نشده است.</p>`}</div>`}
    </${Card}>
  </div>`;
}
