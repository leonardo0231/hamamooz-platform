import { html, useEffect, useState } from '../core/view.js';
import { apiRequest } from '../core/api.js';
import { Badge, Button, Card, ErrorState, PageHeader, Progress, Skeleton, StatCard } from '../components/ui.js';

const fa = value => new Intl.NumberFormat('fa-IR').format(Number(value) || 0);
const list = value => Array.isArray(value) ? value : value?.results ?? [];

export function ReportsPage() {
  const [batches, setBatches] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(null);
  const [form, setForm] = useState({ school: '', academic_year: '', term: '', class_section: '', scope: 'class', page_size: 'a3_landscape' });
  const [creating, setCreating] = useState(false);
  const load = async () => { setLoading(true); try { setBatches(list(await apiRequest('reports/batches/'))); setError(null); } catch (err) { setError(err); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const create = async event => { event.preventDefault(); setCreating(true); try { const payload = { ...form, class_section: form.scope === 'class' ? form.class_section : null }; const batch = await apiRequest('reports/batches/', { method: 'POST', body: payload }); setBatches(current => [batch, ...current]); } catch (err) { setError(err); } finally { setCreating(false); } };
  const totals = batches.reduce((result, batch) => ({ total: result.total + batch.total_count, done: result.done + batch.completed_count, failed: result.failed + batch.failed_count }), { total: 0, done: 0, failed: 0 });
  return html`<div class="page report-workspace">
    <${PageHeader} eyebrow="کارنامه تحلیلی" title="تولید و مشاهده کارنامه‌ها" subtitle="کارنامه رنگی، تحلیل و PDF قابل چاپ برای کلاس یا کل مدرسه"/>
    <section class="stats-grid"><${StatCard} label="بسته‌های گزارش" value=${fa(batches.length)} icon="report" tone="purple"/><${StatCard} label="کارنامه آماده" value=${fa(totals.done)} icon="check" tone="green"/><${StatCard} label="در صف یا تولید" value=${fa(Math.max(0, totals.total - totals.done - totals.failed))} icon="calendar" tone="orange"/><${StatCard} label="نیازمند بررسی" value=${fa(totals.failed)} icon="alert" tone="pink"/></section>
    <${Card} className="report-create" title="تولید گروهی کارنامه" subtitle="شناسه‌های مدرسه، سال، نوبت و در صورت انتخاب کلاس، شناسه کلاس را وارد کنید."><form onSubmit=${create} class="report-create__form">
      ${[['school','شناسه مدرسه'],['academic_year','شناسه سال تحصیلی'],['term','شناسه نوبت']].map(([key,label]) => html`<label>${label}<input required value=${form[key]} onInput=${e => setForm({ ...form, [key]: e.currentTarget.value })}/></label>`)}
      <label>دامنه<select value=${form.scope} onInput=${e => setForm({ ...form, scope: e.currentTarget.value })}><option value="class">کلاس منتخب</option><option value="school">کل مدرسه</option></select></label>
      ${form.scope === 'class' && html`<label>شناسه کلاس<input required value=${form.class_section} onInput=${e => setForm({ ...form, class_section: e.currentTarget.value })}/></label>`}
      <label>اندازه PDF<select value=${form.page_size} onInput=${e => setForm({ ...form, page_size: e.currentTarget.value })}><option value="a3_landscape">A3 افقی</option><option value="a4_portrait">A4 عمودی</option></select></label>
      <div class="report-create__action"><${Button} icon="report" disabled=${creating}>${creating ? 'در حال ثبت…' : 'شروع تولید گروهی'}</${Button}></div>
    </form></${Card}>
    <${Card} title="بسته‌های تولیدشده" subtitle="هر کارنامه مستقل آرشیو می‌شود و پس از اتمام، ZIP آن قابل دریافت است." action=${html`<${Button} variant="outline" onClick=${load}>به‌روزرسانی</${Button}>`}>
      ${loading ? html`<${Skeleton} lines=${5}/>` : error ? html`<${ErrorState} error=${error} onRetry=${load}/>` : html`<div class="report-batches">${batches.map(batch => html`<article class="report-batch"><header><div><strong>${batch.scope === 'school' ? 'کل مدرسه' : 'کلاس منتخب'}</strong><small>تولید ${batch.page_size === 'a3_landscape' ? 'A3 افقی' : 'A4 عمودی'}</small></div><${Badge} tone=${batch.status === 'completed' ? 'success' : batch.status === 'partial' ? 'important' : batch.status === 'failed' ? 'danger' : 'info'}>${batch.status}</${Badge}></header><${Progress} value=${batch.progress_percent} label="پیشرفت تولید"/><footer><span>${fa(batch.completed_count)} آماده از ${fa(batch.total_count)} · ${fa(batch.failed_count)} ناموفق</span>${batch.zip_download_url && html`<a class="button button--outline" href=${batch.zip_download_url}>دانلود ZIP</a>`}</footer></article>`)}${!batches.length && html`<p class="report-empty">هنوز بسته‌ای تولید نشده است.</p>`}</div>`}
    </${Card}>
  </div>`;
}
