import { html, useMemo, useState } from '../core/view.js';
import { useAsyncData } from '../core/hooks.js';
import { dataApi } from '../core/api.js';
import { LineChart } from '../components/charts.js';
import { Avatar, Badge, Button, Card, ErrorState, PageHeader, SearchField, Skeleton, StatCard } from '../components/ui.js';
import { Icon } from '../components/icons.js';

const severity = { critical: ['بحرانی', 'critical'], important: ['مهم', 'important'], review: ['نیازمند بررسی', 'info'] };

export function AlertsPage() {
  const result = useAsyncData(signal => dataApi.alerts({ page_size: 50 }, signal), []);
  const [selectedId, setSelectedId] = useState(1);
  const [query, setQuery] = useState('');
  const [level, setLevel] = useState('all');
  const filtered = useMemo(() => (result.data ?? []).filter(item => (level === 'all' || item.severity === level) && `${item.student} ${item.title}`.includes(query)), [result.data, query, level]);
  const selected = filtered.find(item => item.id === selectedId) ?? filtered[0];
  if (result.status === 'loading') return html`<div class="page"><${Skeleton} lines=${10}/></div>`;
  if (result.status === 'error') return html`<div class="page"><${ErrorState} error=${result.error} onRetry=${result.reload}/></div>`;
  return html`<div class="page page--alerts">
    <${PageHeader} title="مرکز هشدارها و پیگیری" subtitle="هشدارهای آموزشی، رفتاری و حضور و غیاب" actions=${html`<${Button} variant="outline" icon="download">خروجی گزارش</${Button}>`} />
    <section class="stats-grid"><${StatCard} label="بحرانی" value="۴" icon="alert" tone="pink"/><${StatCard} label="مهم" value="۱۲" icon="alert" tone="orange"/><${StatCard} label="نیازمند بررسی" value="۲۶" icon="search" tone="purple"/><${StatCard} label="حل‌شده" value="۳۸" icon="check" tone="green"/></section>
    <${Card} className="alerts-workspace"><div class="alerts-filters"><${SearchField} value=${query} onInput=${event => setQuery(event.currentTarget.value)} placeholder="جست‌وجوی دانش‌آموز…"/><select value=${level} onChange=${event => setLevel(event.currentTarget.value)}><option value="all">همه وضعیت‌ها</option><option value="critical">بحرانی</option><option value="important">مهم</option><option value="review">نیازمند بررسی</option></select><button class="filter-button"><${Icon} name="filter" size=${18}/> فیلتر بیشتر</button></div>
      <div class="alerts-layout"><div class="alert-list" aria-label="فهرست هشدارها">${filtered.map(item => html`<button class=${selected?.id === item.id ? 'is-selected' : ''} onClick=${() => setSelectedId(item.id)}><${Avatar} name=${item.student}/><span class="alert-list__text"><span><strong>${item.student}</strong><${Badge} tone=${severity[item.severity][1]}>${severity[item.severity][0]}</${Badge}></span><small>${item.meta}</small><b>${item.title}</b><time>${item.time}</time></span></button>`)}</div>
      ${selected && html`<article class="alert-detail"><header><div><span><${Badge} tone=${severity[selected.severity][1]}>${severity[selected.severity][0]}</${Badge}></span><div class="alert-detail__person"><${Avatar} name=${selected.student}/><span><strong>${selected.student}</strong><small>${selected.meta}</small></span></div><h2>${selected.title}</h2><p>عملکرد دانش‌آموز طی دوره اخیر کاهش قابل توجهی داشته و نیازمند اقدام هماهنگ آموزشی است.</p></div></header>
        <div class="alert-evidence"><${Card} title="نمودار روند نمرات (ریاضی)"><${LineChart} values=${[16, 12, 8]} labels=${['آزمون اول', 'آزمون دوم', 'آزمون سوم']} color="#6c42f5" title="کاهش نمرات ریاضی"/></${Card}><${Card} title="شواهد و داده‌ها"><ul>${selected.evidence.map(item => html`<li><${Icon} name="check" size=${16}/>${item}</li>`)}</ul></${Card}></div>
        <dl class="alert-meta"><div><dt>ایجادکننده</dt><dd>سامانه هوشمند</dd></div><div><dt>درس مرتبط</dt><dd>ریاضی</dd></div><div><dt>نوع هشدار</dt><dd>${selected.type}</dd></div><div><dt>تاریخ ایجاد</dt><dd>${selected.time}</dd></div></dl>
        <div class="suggested-action"><span><${Icon} name="sparkles" size=${24}/></span><div><h3>اقدام پیشنهادی</h3><p>برگزاری جلسه با دانش‌آموز و ارجاع به مشاور آموزشی برای بررسی علت افت.</p></div><${Button} variant="outline" icon="user">ارجاع به مشاور</${Button}><${Button} variant="success" icon="plus">ایجاد پیگیری</${Button}></div>
      </article>`}</div>
    </${Card}>
  </div>`;
}
