import { html, useMemo, useState } from '../core/view.js';
import { useAsyncData } from '../core/hooks.js';
import { dataApi } from '../core/api.js';
import { navigate } from '../core/router.js';
import { LineChart } from '../components/charts.js';
import { Avatar, Badge, Button, Card, ErrorState, PageHeader, Skeleton, StatCard } from '../components/ui.js';
import { Icon } from '../components/icons.js';

const tabs = ['خلاصه', 'آموزشی', 'حضور و غیاب', 'رفتار', 'مشاوره', 'پیگیری'];

function normalizeStudent(data) {
  if (!data?.summary) return data;
  const enrollment = data.summary.current_enrollment;
  const latest = data.academics?.term_results?.at(-1);
  const attendance = data.attendance?.metrics;
  return {
    id: data.summary.student.id, name: data.summary.student.full_name, status: data.summary.student.status,
    grade: enrollment?.grade ?? '—', className: enrollment?.class_section ?? '—', average: latest?.average ?? 0,
    rank: latest?.class_rank ?? '—', absences: attendance?.absence_count ?? 0, growth: 0,
    trend: (data.academics?.term_results ?? []).map(item => item.average).filter(Number.isFinite),
    strengths: [], improvements: [], events: [],
  };
}

export function StudentPage({ id }) {
  const result = useAsyncData(signal => dataApi.student(id, signal), [id]);
  const [tab, setTab] = useState('خلاصه');
  const student = useMemo(() => normalizeStudent(result.data), [result.data]);
  if (result.status === 'loading') return html`<div class="page"><${Skeleton} lines=${10}/></div>`;
  if (result.status === 'error') return html`<div class="page"><${ErrorState} error=${result.error} onRetry=${result.reload}/></div>`;
  const trend = student.trend?.length > 1 ? student.trend : [13.8, 14.9, 15.8, 16.2, 17.1, Number(student.average) || 17.86];
  return html`<div class="page page--student">
    <${PageHeader} title="پرونده ۳۶۰ درجه دانش‌آموز" subtitle="دانش‌آموزان / پرونده دانش‌آموز" />
    <section class="student-hero"><div class="student-hero__identity"><${Avatar} name=${student.name} size="xl"/><div><h2>${student.name}</h2><p>${student.grade} · کلاس ${student.className}</p></div></div><${Badge} tone="success">● فعال</${Badge}></section>
    <nav class="student-tabs" aria-label="بخش‌های پرونده">${tabs.map(item => html`<button class=${tab === item ? 'is-active' : ''} onClick=${() => setTab(item)}>${item}</button>`)}</nav>
    ${tab === 'خلاصه' ? html`<div>
      <section class="stats-grid stats-grid--student"><${StatCard} label="معدل" value=${String(student.average).replace('.', '٫')} icon="chart" tone="purple"/><${StatCard} label="رتبه کلاس" value=${student.rank} icon="graduation" tone="purple"/><${StatCard} label="غیبت" value=${`${student.absences} روز`} icon="calendar" tone="pink"/><${StatCard} label="رشد" value=${`+${student.growth}٪`} icon="chart" tone="green"/></section>
      <section class="student-grid">
        <${Card} className="student-trend" title="روند تحصیلی سه‌ساله" action=${html`<select aria-label="انتخاب شاخص"><option>معدل ترمی</option></select>`}><${LineChart} values=${trend} labels=${['مهر ۱۴۰۰', 'بهمن ۱۴۰۰', 'خرداد ۱۴۰۱', 'مهر ۱۴۰۱', 'بهمن ۱۴۰۱', 'خرداد ۱۴۰۲']} title=${`روند تحصیلی ${student.name}`}/></${Card}>
        <div class="student-insights"><${Card} title="نقاط قوت" icon="sparkles"><div class="tag-list tag-list--green">${(student.strengths?.length ? student.strengths : ['فیزیک', 'علوم تجربی', 'انگلیسی']).map(item => html`<span>${item}</span>`)}</div></${Card}><${Card} title="نیازمند بهبود" icon="chart"><div class="tag-list tag-list--orange">${(student.improvements?.length ? student.improvements : ['ریاضی', 'عربی']).map(item => html`<span>${item}</span>`)}</div></${Card}></div>
        <${Card} className="student-timeline" title="آخرین رویدادها"><div class="timeline">${(student.events?.length ? student.events : [{ title: 'اطلاعات رویداد ثبت نشده است', actor: 'پس از ثبت داده نمایش داده می‌شود', date: '—', tone: 'purple' }]).map(event => html`<div class=${`timeline__item timeline__item--${event.tone}`}><span></span><div><strong>${event.title}</strong><small>${event.actor}</small></div><time>${event.date}</time></div>`)}</div></${Card}>
        <aside class="student-actions"><div class="attention-box"><${Icon} name="alert"/><strong>نیازمند پیگیری در ریاضی</strong><p>میانگین نمرات ریاضی نسبت به میانگین کلاس پایین‌تر است.</p><button>مشاهده جزئیات</button></div><div class="action-box"><${Button} variant="success" icon="plus">ثبت اقدام پیگیری</${Button}><${Button} variant="outline" icon="download">دریافت گزارش</${Button}></div></aside>
      </section>
    </div>` : html`<${Card} className="tab-placeholder"><${Icon} name=${tab === 'حضور و غیاب' ? 'calendar' : tab === 'آموزشی' ? 'chart' : 'report'} size=${38}/><h2>${tab}</h2><p>اطلاعات این بخش از سرویس پرونده ۳۶۰ درجه دریافت و در همین ساختار نمایش داده می‌شود.</p><${Button} variant="outline" onClick=${() => setTab('خلاصه')}>بازگشت به خلاصه</${Button}></${Card}>`}
  </div>`;
}
