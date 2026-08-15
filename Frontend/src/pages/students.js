import { html, useMemo, useState } from '../core/view.js';
import { useAsyncData } from '../core/hooks.js';
import { dataApi } from '../core/api.js';
import { navigate } from '../core/router.js';
import { Avatar, Badge, Button, Card, EmptyState, ErrorState, PageHeader, Progress, SearchField, Skeleton } from '../components/ui.js';
import { Icon } from '../components/icons.js';

const riskTone = { critical: 'critical', important: 'important', review: 'info', none: 'success' };
const riskLabel = { critical: 'بحرانی', important: 'نیازمند توجه', review: 'تحت بررسی', none: 'عادی' };

export function StudentsPage() {
  const result = useAsyncData(signal => dataApi.students({ page_size: 50 }, signal), []);
  const [query, setQuery] = useState('');
  const [grade, setGrade] = useState('همه');
  const filtered = useMemo(() => (result.data ?? []).filter(student => (grade === 'همه' || student.grade === grade) && `${student.name} ${student.code}`.includes(query)), [result.data, query, grade]);

  if (result.status === 'loading') return html`<div class="page"><${Skeleton} lines=${10}/></div>`;
  if (result.status === 'error') return html`<div class="page"><${ErrorState} error=${result.error} onRetry=${result.reload}/></div>`;
  return html`<div class="page page--students">
    <${PageHeader} eyebrow="مدیریت آموزشی" title="دانش‌آموزان" subtitle="مشاهده، جست‌وجو و دسترسی به پرونده ۳۶۰ درجه دانش‌آموزان" actions=${html`<${Button} variant="outline" icon="upload" onClick=${() => navigate('/imports')}>ورود اطلاعات</${Button}><${Button} icon="plus">دانش‌آموز جدید</${Button}>`}/>
    <${Card} className="filters-card"><div class="filters-row"><${SearchField} value=${query} onInput=${event => setQuery(event.currentTarget.value)} placeholder="نام، کد دانش‌آموزی یا کلاس…"/><select value=${grade} onChange=${event => setGrade(event.currentTarget.value)} aria-label="فیلتر پایه"><option>همه</option><option>پایه هشتم</option><option>پایه نهم</option><option>پایه دهم</option><option>پایه یازدهم</option></select><button class="filter-button"><${Icon} name="filter" size=${18}/> فیلترهای بیشتر</button><span class="result-count">${filtered.length} دانش‌آموز</span></div></${Card}>
    ${filtered.length ? html`<${Card} className="data-table-card"><div class="table-scroll"><table class="data-table"><thead><tr><th>دانش‌آموز</th><th>پایه و کلاس</th><th>میانگین</th><th>حضور</th><th>وضعیت پیگیری</th><th><span class="sr-only">عملیات</span></th></tr></thead><tbody>${filtered.map(student => html`<tr key=${student.id} onClick=${() => navigate(`/students/${student.id}`)}><td><div class="person-cell"><${Avatar} name=${student.name}/><span><strong>${student.name}</strong><small>${student.code}</small></span></div></td><td>${student.grade} · ${student.className}</td><td><strong>${String(student.average).replace('.', '٫')}</strong></td><td><div class="attendance-cell"><span>${student.attendance}٪</span><${Progress} value=${student.attendance} label=${`حضور ${student.name}`}/></div></td><td><${Badge} tone=${riskTone[student.risk]}>${riskLabel[student.risk]}</${Badge}></td><td><button class="icon-button" onClick=${event => { event.stopPropagation(); navigate(`/students/${student.id}`); }} aria-label=${`مشاهده پرونده ${student.name}`}><${Icon} name="chevron" size=${17}/></button></td></tr>`)}</tbody></table></div></${Card}>` : html`<${EmptyState} title="دانش‌آموزی مطابق فیلترها پیدا نشد"/>`}
  </div>`;
}
