import { html, useEffect, useMemo, useRef, useState } from '../core/view.js';
import { useAsyncData } from '../core/hooks.js';
import { apiRequest, dataApi } from '../core/api.js';
import { config } from '../core/config.js';
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
    photo: data.identity?.photo ?? null,
    grade: enrollment?.grade ?? '—', className: enrollment?.class_section ?? '—', average: latest?.average ?? 0,
    rank: latest?.class_rank ?? '—', absences: attendance?.absence_count ?? 0, growth: 0,
    trend: (data.academics?.term_results ?? []).map(item => item.average).filter(Number.isFinite),
    strengths: [], improvements: [], events: [],
  };
}

const imageTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);

function photoError(file) {
  if (!file) return 'فایل تصویر انتخاب نشده است.';
  if (!imageTypes.has(file.type)) return 'فقط تصویر JPG، PNG یا WebP پذیرفته می‌شود.';
  if (file.size > 2 * 1024 * 1024) return 'حجم تصویر باید حداکثر ۲ مگابایت باشد.';
  return null;
}

function StudentPhoto({ student, onChange }) {
  const input = useRef(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const upload = async event => {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    const validation = photoError(file);
    if (validation) { setMessage({ tone: 'error', text: validation }); return; }

    const localUrl = URL.createObjectURL(file);
    setPreview(previous => { if (previous) URL.revokeObjectURL(previous); return localUrl; });
    setUploading(true);
    setMessage(null);
    if (config.demoMode) {
      onChange(localUrl);
      setUploading(false);
      setMessage({ tone: 'success', text: 'عکس در حالت نمایشی به‌روزرسانی شد.' });
      return;
    }
    const body = new FormData();
    body.set('photo', file);
    try {
      const updated = await apiRequest(`students/${student.id}/`, { method: 'PATCH', body });
      onChange(updated.photo ?? localUrl);
      setMessage({ tone: 'success', text: 'عکس دانش‌آموز با موفقیت ذخیره شد.' });
    } catch (error) {
      setPreview(previous => { if (previous) URL.revokeObjectURL(previous); return null; });
      setMessage({ tone: 'error', text: error.message ?? 'ذخیرهٔ عکس انجام نشد.' });
    } finally {
      setUploading(false);
    }
  };

  return html`<div class="student-photo-control">
    <${Avatar} name=${student.name} src=${preview ?? student.photo} size="xl"/>
    <input ref=${input} class="sr-only" id="student-photo-input" type="file" accept="image/jpeg,image/png,image/webp" onChange=${upload}/>
    <button class="student-photo-control__trigger" type="button" onClick=${() => input.current?.click()} disabled=${uploading} aria-label="آپلود یا تغییر عکس دانش‌آموز">
      <${Icon} name="upload" size=${16}/>${uploading ? 'در حال ذخیره…' : 'تغییر عکس'}
    </button>
    ${message && html`<small class=${`student-photo-control__message is-${message.tone}`} role=${message.tone === 'error' ? 'alert' : 'status'}>${message.text}</small>`}
  </div>`;
}

export function StudentPage({ id }) {
  const result = useAsyncData(signal => dataApi.student(id, signal), [id]);
  const [tab, setTab] = useState('خلاصه');
  const [uploadedPhoto, setUploadedPhoto] = useState(null);
  const student = useMemo(() => normalizeStudent(result.data), [result.data]);
  if (result.status === 'loading') return html`<div class="page"><${Skeleton} lines=${10}/></div>`;
  if (result.status === 'error') return html`<div class="page"><${ErrorState} error=${result.error} onRetry=${result.reload}/></div>`;
  const trend = student.trend?.length > 1 ? student.trend : [13.8, 14.9, 15.8, 16.2, 17.1, Number(student.average) || 17.86];
  const presentedStudent = { ...student, photo: uploadedPhoto ?? student.photo };
  return html`<div class="page page--student">
    <${PageHeader} title="پرونده ۳۶۰ درجه دانش‌آموز" subtitle="دانش‌آموزان / پرونده دانش‌آموز" />
    <section class="student-hero"><div class="student-hero__identity"><${StudentPhoto} student=${presentedStudent} onChange=${setUploadedPhoto}/><div><h2>${student.name}</h2><p>${student.grade} · کلاس ${student.className}</p></div></div><${Badge} tone="success">● فعال</${Badge}></section>
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
