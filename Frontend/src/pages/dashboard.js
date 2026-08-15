import { html } from '../core/view.js';
import { useAsyncData } from '../core/hooks.js';
import { dataApi } from '../core/api.js';
import { navigate } from '../core/router.js';
import { BarChart, LineChart } from '../components/charts.js';
import { Badge, Button, Card, ErrorState, PageHeader, Skeleton, StatCard } from '../components/ui.js';
import { Icon } from '../components/icons.js';

const followups = [
  ['افت تحصیلی', 'سارا محمدی · پایه یازدهم', 'critical'], ['غیبت غیرموجه', 'علی رضایی · پایه دهم', 'important'],
  ['بهبود عملکرد', 'پارسا کریمی · پایه دوازدهم', 'success'], ['تأخیر در تکالیف', 'نیلوفر حیدری · پایه یازدهم', 'critical'],
];

function DashboardContent({ data }) {
  return html`<div class="page page--dashboard">
    <${PageHeader} eyebrow="نمای کلی مدرسه" title="صبح بخیر، مریم نادری" subtitle=${`نمای کلی عملکرد مدرسه در سال تحصیلی ${data.academicYear}`} actions=${html`<${Button} variant="outline" icon="download">خروجی گزارش</${Button}><${Button} icon="plus">اقدام جدید</${Button}>`} />
    <section class="stats-grid" aria-label="شاخص‌های کلیدی">${data.kpis.map(item => html`<${StatCard} ...${item} />`)}</section>
    <section class="dashboard-grid">
      <${Card} className="dashboard-chart dashboard-chart--main" title="روند عملکرد مدرسه" subtitle="میانگین وزنی مدرسه در ۷ ماه اخیر" icon="chart"><${LineChart} values=${data.performance} labels=${data.months} title="روند میانگین عملکرد مدرسه" /></${Card}>
      <${Card} className="dashboard-chart" title="مقایسه پایه‌ها" subtitle="میانگین نمرات دروس اصلی" icon="chart"><${BarChart} items=${data.grades} /></${Card}>
      <${Card} className="followups" title="پیگیری‌های فوری" icon="alert" action=${html`<button class="text-button" onClick=${() => navigate('/alerts')}>مشاهده همه</button>`}>
        <div class="followups__list">${followups.map(([title, meta, tone]) => html`<button onClick=${() => navigate('/alerts')}><span><strong>${title}</strong><small>${meta}</small></span><${Badge} tone=${tone}>${tone === 'critical' ? 'بحرانی' : tone === 'important' ? 'نیازمند توجه' : 'در حال بهبود'}</${Badge}><${Icon} name="chevron" size=${15}/></button>`)}</div>
        <${Button} variant="success" icon="report" className="button--block" onClick=${() => navigate('/alerts')}>مشاهده همه پیگیری‌ها</${Button}>
      </${Card}>
    </section>
    <section class="report-banner"><div class="report-banner__art"><${Icon} name="report" size=${48}/></div><div><strong>گزارش تحلیلی عملکرد نیم‌سال اول</strong><p>گزارش کامل وضعیت آموزشی، حضور و غیاب و روند پیشرفت دانش‌آموزان</p></div><${Button} variant="success" icon="report" onClick=${() => navigate('/reports')}>مشاهده گزارش کامل</${Button}></section>
  </div>`;
}

export function DashboardPage() {
  const result = useAsyncData(signal => dataApi.dashboard(signal), []);
  if (result.status === 'loading') return html`<div class="page"><${Skeleton} lines=${8}/></div>`;
  if (result.status === 'error') return html`<div class="page"><${ErrorState} error=${result.error} onRetry=${result.reload}/></div>`;
  return html`<${DashboardContent} data=${result.data}/>`;
}
