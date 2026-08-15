import { html } from '../core/view.js';
import { genericPageData } from '../core/mock-data.js';
import { BarChart, LineChart } from '../components/charts.js';
import { Badge, Button, Card, PageHeader, StatCard } from '../components/ui.js';
import { Icon } from '../components/icons.js';

const sampleRows = [
  ['امیرحسین رضایی', 'پایه نهم', 'امروز، ۱۰:۳۰', 'نیازمند پیگیری'],
  ['نرگس موسوی', 'پایه هشتم', 'امروز، ۰۹:۱۵', 'در حال بررسی'],
  ['علی محمدی', 'پایه دهم', 'دیروز، ۱۴:۴۵', 'تکمیل‌شده'],
  ['سارا احمدی', 'پایه نهم', 'دیروز، ۱۱:۲۰', 'نیازمند پیگیری'],
];

export function GenericPage({ kind, tag }) {
  const info = genericPageData[kind] ?? {
    title: tag ? `مدیریت ${tag.replaceAll('-', ' ')}` : 'مدیریت اطلاعات', subtitle: 'مشاهده و مدیریت اطلاعات حوزه فعال', icon: 'folder',
    metrics: [['کل رکوردها', '۱۲۸'], ['فعال', '۹۶'], ['امروز', '۱۴'], ['نیازمند بررسی', '۸']],
  };
  return html`<div class="page page--generic">
    <${PageHeader} eyebrow="پنل مدیریتی" title=${info.title} subtitle=${info.subtitle} actions=${html`<${Button} variant="outline" icon="download">خروجی گزارش</${Button}><${Button} icon="plus">ثبت مورد جدید</${Button}>`}/>
    <section class="stats-grid">${info.metrics.map(([label, value], index) => html`<${StatCard} label=${label} value=${value} icon=${[info.icon, 'chart', 'calendar', 'alert'][index]} tone=${['purple', 'green', 'orange', 'pink'][index]}/>`)} </section>
    <section class="generic-grid"><${Card} className="generic-grid__chart" title="روند شش‌ماهه" subtitle="نمایش تغییرات شاخص اصلی"><${LineChart} values=${[13.8, 14.4, 15.2, 15.9, 16.4, 17.1]} labels=${['مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']} /></${Card}><${Card} title="مقایسه وضعیت‌ها"><${BarChart} items=${[{ label: 'هشتم', value: 15.9 }, { label: 'نهم', value: 16.4 }, { label: 'دهم', value: 17.1 }]} color="#663bf2"/></${Card}></section>
    <${Card} title="آخرین موارد" action=${html`<button class="text-button">مشاهده همه</button>`}><div class="table-scroll"><table class="data-table"><thead><tr><th>عنوان</th><th>گروه</th><th>آخرین تغییر</th><th>وضعیت</th><th></th></tr></thead><tbody>${sampleRows.map(row => html`<tr>${row.slice(0, 3).map(cell => html`<td>${cell}</td>`)}<td><${Badge} tone=${row[3] === 'تکمیل‌شده' ? 'success' : row[3] === 'در حال بررسی' ? 'info' : 'important'}>${row[3]}</${Badge}></td><td><button class="icon-button" aria-label="مشاهده جزئیات"><${Icon} name="chevron" size=${16}/></button></td></tr>`)}</tbody></table></div></${Card}>
  </div>`;
}
