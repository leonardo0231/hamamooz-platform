import { html, useMemo } from '../core/view.js';
import { EChart } from './echart.js';

const fa = value => value === null || value === undefined || value === '' || Number.isNaN(Number(value))
  ? '—'
  : new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(Number(value));
const clamp = (value, min = 0, max = 100) => Math.max(min, Math.min(max, Number(value) || 0));
const isNumber = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));

const metricTitles = {
  EDU_01: 'نمرات درسی', EDU_02: 'پیشرفت نسبت به قبل', EDU_03: 'انجام تکالیف', EDU_04: 'مشارکت در کلاس', EDU_05: 'دقت و تمرکز',
  DEV_01: 'احترام و همکاری', DEV_02: 'مسئولیت‌پذیری', DEV_04: 'نظم شخصی', DEV_10: 'اعتماد به نفس',
  CHR_01: 'خودکنترلی', CHR_02: 'انگیزه برای یادگیری', CHR_03: 'پشتکار', CHR_08: 'مدیریت استرس',
  DIS_01: 'حضور و غیاب', DIS_03: 'رعایت قوانین', PER_01: 'مدیریت زمان', PER_02: 'مهارت ارتباطی',
  PER_04: 'کار تیمی', PER_05: 'تفکر انتقادی',
};

const demo = {
  demo: true,
  organization: 'سامانه هوشمند هم‌آموز',
  school: 'دبیرستان پسرانه بعثت',
  schoolLogoUrl: '',
  student: { name: 'آرین محمدی', nationalId: '۰۰۱۲۳۴۵۶۷۸', number: '۹۹-۲۰۲۴', initial: 'آ', photoUrl: '' },
  academic: { year: '۱۴۰۴–۱۴۰۵', grade: 'پایه نهم', className: 'نهم / الف', term: 'نوبت اول' },
  average: 18.78,
  rank: 3,
  history: [
    { label: 'پایه هفتم', average: 16.2, rank: 12 },
    { label: 'پایه هشتم', average: 17.45, rank: 7 },
    { label: 'پایه نهم', average: 18.78, rank: 3 },
  ],
  subjects: [
    { title: 'معدل کل', first: 16.2, previous: 17.45, current: 18.78, continuous: 18.6, midterm: 18.8, final: 19 },
    { title: 'ریاضی', first: 17.3, previous: 18.1, current: 19.5, continuous: 19.2, midterm: 19.4, final: 19.8 },
    { title: 'علوم تجربی', first: 16, previous: 17.2, current: 18.9, continuous: 18.7, midterm: 18.8, final: 19.1 },
    { title: 'فارسی', first: 16.2, previous: 17, current: 18.4, continuous: 18.3, midterm: 18.5, final: 18.5 },
    { title: 'عربی', first: 15.4, previous: 16.7, current: 17.2, continuous: 17, midterm: 17.2, final: 17.4 },
    { title: 'زبان انگلیسی', first: 17, previous: 18.2, current: 19.2, continuous: 19, midterm: 19.2, final: 19.4 },
    { title: 'مطالعات اجتماعی', first: 16.1, previous: 16.8, current: 18.1, continuous: 18, midterm: 18.1, final: 18.2 },
  ],
  skills: [
    { title: 'احترام و همکاری', value: 92 }, { title: 'مسئولیت‌پذیری', value: 88 }, { title: 'اعتماد به نفس', value: 84 },
    { title: 'نظم شخصی', value: 91 }, { title: 'خودکنترلی', value: 86 }, { title: 'مدیریت زمان', value: 78 },
  ],
  skills21: [
    { title: 'ارتباط مؤثر', value: 86 }, { title: 'تفکر انتقادی', value: 82 }, { title: 'حل مسئله', value: 90 },
    { title: 'خلاقیت', value: 88 }, { title: 'کار گروهی', value: 92 }, { title: 'خودمدیریتی', value: 84 },
  ],
  readiness: [
    { title: 'ریاضی', value: 90 }, { title: 'علوم', value: 85 }, { title: 'زبان و ادبیات', value: 88 },
    { title: 'زبان انگلیسی', value: 92 }, { title: 'مهارت مطالعه', value: 81 }, { title: 'اعتماد به نفس', value: 84 },
  ],
  strengths: [
    { title: 'قدرت تحلیل', value: 90 }, { title: 'حل مسئله', value: 85 }, { title: 'دقت و تمرکز', value: 80 },
    { title: 'خلاقیت', value: 75 }, { title: 'مسئولیت‌پذیری', value: 90 }, { title: 'مدیریت زمان', value: 70 },
  ],
  improvements: [
    { title: 'تمرکز در مطالعه', value: 60 }, { title: 'برنامه‌ریزی درسی', value: 65 }, { title: 'مشارکت در کلاس', value: 55 },
    { title: 'سرعت عمل', value: 60 }, { title: 'مطالعه روزانه', value: 70 },
  ],
  activities: [
    { icon: '🏅', title: 'المپیاد علمی', text: 'مقام دوم منطقه' }, { icon: '⚽', title: 'مسابقات ورزشی', text: 'عضو تیم مدرسه' },
    { icon: '🔬', title: 'پژوهش و تحلیل', text: 'پروژه برگزیده' }, { icon: '📚', title: 'باشگاه کتاب‌خوانی', text: 'مشارکت مستمر' },
  ],
  awards: [{ icon: '🏅', title: 'المپیاد علمی', text: 'مقام دوم منطقه' }, { icon: '🎖', title: 'دانش‌آموز منظم', text: 'نوبت اول ۱۴۰۴' }, { icon: '🏆', title: 'پژوهش برتر', text: 'نمایشگاه مدرسه' }],
  counselor: ['روند پیشرفت در سه سال پایدار و رو به رشد است.', 'اعتماد به نفس در ارائه‌های کلاسی تقویت شود.', 'برای مدیریت زمان، برنامه هفتگی مشترک تنظیم شود.'],
  recommendations: ['برنامه ثابت مطالعه روزانه برای تثبیت رشد ادامه یابد.', 'در پروژه‌های پژوهشی و کارگروهی نقش ارائه‌دهنده تجربه شود.'],
  teacherRecommendations: ['تمرین‌های چالشی ریاضی به‌صورت هفتگی پیگیری شود.', 'بازخورد کوتاه و مشخص پس از ارائه‌های کلاسی ارائه شود.'],
  followUps: ['پیگیری منظم تکالیف و پروژه‌ها', 'تقویت مهارت ارائه در فعالیت‌های کلاسی', 'مشارکت بیشتر در گروه‌های پژوهشی'],
  support: ['همراهی خانواده در مرور برنامه هفتگی', 'گفت‌وگوی کوتاه ماهانه با مشاور مدرسه'],
  attendance: { rate: 96, sessions: 42, unexcused: 1, late: 2 },
  accessCode: 'BAH-1405-99',
  accessHref: '/reports',
};

function titleForMetric(code) { return metricTitles[code] ?? String(code || '').replace('_', ' '); }
function metricValue(value) { return clamp(Number(value) * 20); }
function numericSubject(row) { return isNumber(row?.average) ? Number(row.average) : null; }

function mapSnapshot(snapshot) {
  const report = snapshot?.reports?.[0];
  if (!report) return demo;
  const context = report.product_context ?? {};
  const latest = context.evaluations?.at?.(-1);
  const rawMetrics = latest?.metrics ?? latest?.metric_scores ?? {};
  const metrics = Array.isArray(rawMetrics)
    ? rawMetrics
    : Object.entries(rawMetrics).map(([code, value]) => ({ code, title: titleForMetric(code), value }));
  const metricRows = metrics.map(item => ({ ...item, title: item.title ?? titleForMetric(item.code), value: metricValue(item.value) }));
  const behavior = metricRows.filter(item => /^(DEV|CHR|DIS)_/.test(item.code ?? '')).slice(0, 6);
  const skills21 = metricRows.filter(item => /^(PER|DEV|CHR)_/.test(item.code ?? '')).slice(0, 6);
  const subjectRows = (report.subjects ?? []).map(item => ({
    title: item.title, current: numericSubject(item), first: numericSubject(item.first), previous: numericSubject(item.previous),
    continuous: numericSubject(item.continuous), midterm: numericSubject(item.midterm), final: numericSubject(item.final), passed: item.passed,
  }));
  const history = (report.history ?? []).filter(item => isNumber(item.average)).map(item => ({ label: item.label, average: Number(item.average), rank: item.rank ?? null }));
  const academic = metricRows.filter(item => /^(EDU|PER)_/.test(item.code ?? '')).slice(0, 6);
  const strengths = [...subjectRows].filter(item => isNumber(item.current)).sort((a, b) => b.current - a.current).slice(0, 6).map(item => ({ title: item.title, value: clamp(item.current * 5) }));
  const improvements = [...subjectRows].filter(item => isNumber(item.current)).sort((a, b) => a.current - b.current).slice(0, 6).map(item => ({ title: item.title, value: clamp(item.current * 5) }));
  const attendance = context.attendance ?? {};
  const attendanceRate = isNumber(attendance.attendance_rate) ? Number(attendance.attendance_rate) : isNumber(attendance.present_rate) ? Number(attendance.present_rate) : null;
  const recommendations = context.approved_recommendations ?? [];
  const activities = (context.activities ?? []).slice(0, 6).map(item => ({
    icon: item.kind === 'sport' ? '⚽' : item.kind === 'research' ? '🔬' : item.kind === 'competition' ? '🏅' : '✦',
    title: item.title, text: item.result || (item.placement ? `رتبه ${fa(item.placement)}` : 'ثبت‌شده'),
  }));
  const awards = activities.filter(item => item.text !== 'ثبت‌شده').slice(0, 4);
  return {
    demo: false, organization: report.organization?.name ?? 'سامانه هم‌آموز', school: report.school?.name ?? 'مدرسه', schoolLogoUrl: report.school?.logo_url ?? '',
    student: { name: report.student?.full_name ?? 'دانش‌آموز', nationalId: report.student?.national_id ?? '—', number: report.student?.student_number ?? '—', initial: (report.student?.full_name ?? 'د').slice(0, 1), photoUrl: report.student?.photo_url ?? '' },
    academic: { year: report.academic?.year ?? '—', grade: report.academic?.grade ?? '—', className: report.academic?.class ?? '—', term: report.academic?.term ?? '—' },
    average: isNumber(report.summary?.average) ? Number(report.summary.average) : null, rank: report.summary?.class_rank ?? null, history,
    subjects: subjectRows, skills: behavior, skills21, readiness: academic,
    strengths, improvements, activities, awards,
    counselor: (context.counselor_report?.items ?? context.analytics_signals ?? []).map(item => typeof item === 'string' ? item : item.explanation).filter(Boolean).slice(0, 4),
    recommendations: recommendations.filter(item => ['parent', 'student'].includes(item.audience)).map(item => item.approved_text).filter(Boolean).slice(0, 4),
    teacherRecommendations: recommendations.filter(item => ['teacher', 'guide_teacher', 'educational_deputy'].includes(item.audience)).map(item => item.approved_text).filter(Boolean).slice(0, 4),
    followUps: (context.analytics_signals ?? []).map(item => item.explanation).filter(Boolean).slice(0, 4),
    support: (context.support_notes ?? []).map(item => typeof item === 'string' ? item : item.text).filter(Boolean).slice(0, 3),
    attendance: { rate: attendanceRate, sessions: attendance.finalized_session_count ?? null, unexcused: attendance.unexcused_absence_count ?? null, late: attendance.late_count ?? null },
    accessCode: report.id ?? 'REPORT',
    accessHref: report.id ? `/reports?report=${encodeURIComponent(report.id)}` : '/reports',
  };
}

function trendOption(points) {
  if (!points?.length) return null;
  return { color: ['#0f766e'], textStyle: { fontFamily: 'Vazirmatn' }, tooltip: { trigger: 'axis', confine: true, valueFormatter: value => `${fa(value)} از ۲۰` }, grid: { top: 24, right: 12, bottom: 38, left: 32 },
    xAxis: { type: 'category', data: points.map(item => shortTrendLabel(item.label)), axisTick: { show: false }, axisLine: { lineStyle: { color: '#cbd5e1' } }, axisLabel: { color: '#475569', fontSize: 11, fontFamily: 'Vazirmatn', interval: 0, margin: 12, hideOverlap: true } },
    yAxis: { type: 'value', min: 10, max: 20, splitNumber: 4, axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Vazirmatn' }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } },
    series: [{ name: 'میانگین', type: 'line', smooth: true, data: points.map(item => item.average), symbolSize: 9, lineStyle: { width: 4 }, areaStyle: { color: 'rgba(15,118,110,.16)' }, itemStyle: { borderColor: '#fff', borderWidth: 2 } }],
  };
}

function shortTrendLabel(label) { return String(label || '').replace(/^پایه\s*/, ''); }

function radarOption(items) {
  if (!items?.length) return null;
  return { textStyle: { fontFamily: 'Vazirmatn' }, tooltip: { confine: true }, radar: { radius: '46%', center: ['50%', '51%'], axisNameGap: 6, indicator: items.map((item, index) => ({ name: String(index + 1), title: item.title, max: 100 })), splitNumber: 4, splitArea: { areaStyle: { color: ['#fff', '#f2faf8'] } }, axisName: { color: 'transparent', fontSize: 11, fontWeight: 900, fontFamily: 'Vazirmatn', formatter: () => '' }, splitLine: { lineStyle: { color: '#cbd5e1' } }, axisLine: { lineStyle: { color: '#dbeafe' } } },
    series: [{ type: 'radar', symbol: 'circle', symbolSize: 6, data: [{ value: items.map(item => item.value), name: 'ارزیابی مهارت‌ها', areaStyle: { color: 'rgba(14,116,144,.22)' }, lineStyle: { color: '#0e7490', width: 2.5 }, itemStyle: { color: '#0e7490' } }] }],
  };
}

function barsOption(items, color) {
  if (!items?.length) return null;
  return { textStyle: { fontFamily: 'Vazirmatn' }, tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: value => `${fa(value)}٪` }, grid: { top: 4, right: 30, bottom: 3, left: 112, containLabel: true }, xAxis: { type: 'value', max: 100, show: false },
    yAxis: { type: 'category', inverse: true, data: items.map(item => item.title), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { show: true, color: '#475569', fontSize: 10, fontFamily: 'Vazirmatn', width: 106, overflow: 'truncate', align: 'right' } },
    series: [{ type: 'bar', data: items.map(item => item.value), barWidth: 14, showBackground: true, backgroundStyle: { color: '#edf2f7', borderRadius: 7 }, label: { show: true, position: 'right', color: '#475569', formatter: ({ value }) => `${fa(value)}٪`, fontFamily: 'Vazirmatn', fontSize: 10 }, itemStyle: { color, borderRadius: 7 } }],
  };
}

function Panel({ title, tone = 'teal', className = '', children, action }) {
  const displayTitle = title === 'مهارت‌های قرن بیست‌ویکم' ? 'مهارت‌های زندگی و شایستگی‌های قرن ۲۱' : title;
  const body = className.includes('analytical-access') ? html`<a class="report-access-link" href="/reports" aria-label="مشاهدهٔ کارنامه در سامانه">${children}</a>` : children;
  return html`<section class=${`analytical-panel analytical-panel--${tone} ${className}`}><header class="analytical-panel__header"><h3>${displayTitle}</h3>${action && html`<span>${action}</span>`}</header><div class="analytical-panel__body">${body}</div></section>`;
}
function Empty() { return html`<p class="analytical-empty">داده کافی نیست</p>`; }
function Stars({ value }) { const rounded = Math.round((Number(value) || 0) / 20); return html`<span class="report-stars" aria-label=${`${fa(value)} درصد`}>${[1, 2, 3, 4, 5].map(index => html`<span class=${index <= rounded ? 'is-on' : ''}>★</span>`)}</span>`; }
function Avatar({ report }) {
  if (report.student.photoUrl) return html`<img src=${report.student.photoUrl} alt=${`عکس ${report.student.name}`} />`;
  if (!report.demo) return html`<span class="report-avatar-fallback">${report.student.initial}</span>`;
  return html`<svg class="report-avatar-demo" viewBox="0 0 120 145" role="img" aria-label="آواتار نمونه دانش‌آموز"><rect width="120" height="145" rx="12" fill="#d8ebe8"/><circle cx="60" cy="53" r="28" fill="#f1bd91"/><path d="M32 48c2-32 55-43 60-1-11-9-41-14-60 1Z" fill="#273b4a"/><path d="M24 137c5-38 20-53 36-53s31 15 36 53" fill="#143e54"/><path d="M45 67c10 8 20 8 30 0" fill="none" stroke="#9b5f4d" stroke-width="3" stroke-linecap="round"/><circle cx="50" cy="51" r="3" fill="#21303a"/><circle cx="70" cy="51" r="3" fill="#21303a"/></svg>`;
}
const qrRows = ['111111100101011111111', '100000101110010000001', '101110100011010111101', '101110101101010111101', '101110100010010111101', '100000101011010000001', '111111101010011111111', '000000001101000000000', '110111101001111010101', '001010010111000110010', '111001111010111001111', '010111000110101010100', '101000111001010111001', '000000001011101000111', '111111101110010010110', '100000100101111001001', '101110101011001111100', '101110100110100101010', '101110101001111010001', '100000101110001100111', '111111101001101010101'];
function QrCode() { return html`<div class="report-qr" aria-label="کد دسترسی کارنامه">${qrRows.flatMap((row, y) => [...row].map((cell, x) => html`<i class=${cell === '1' ? 'is-dark' : ''} style=${`--x:${x};--y:${y}`}></i>`))}</div>`; }

export function AnalyticalReport({ snapshot, loading = false }) {
  const report = useMemo(() => mapSnapshot(snapshot), [snapshot]);
  const trend = trendOption(report.history); const radar = radarOption(report.skills); const strengths = barsOption(report.strengths, '#0f766e'); const improvements = barsOption(report.improvements, '#a61d4d'); const readiness = barsOption(report.readiness, '#08766f');
  const attendanceRate = isNumber(report.attendance.rate) ? report.attendance.rate : null;
  return html`<article class="analytical-sheet" aria-label=${`کارنامه تحلیلی ${report.student.name}`}>
    <header class="analytical-sheet__header"><div class="analytical-sheet__mark">${report.schoolLogoUrl ? html`<img src=${report.schoolLogoUrl} alt="لوگوی مدرسه"/>` : html`<span>بعثت</span><small>هم‌آموز</small>`}</div><div class="analytical-sheet__heading"><p>کارنامه جامع رشد و تحلیل دانش‌آموز</p><h2>${report.academic.grade}</h2><strong>${report.school}</strong></div><blockquote>« هیچ تلاشی بی‌نتیجه نیست؛<br/>هر قدم کوچک امروز، آینده‌ای بزرگ می‌سازد. »</blockquote></header>
    <div class="analytical-sheet__subhead"><span>${report.organization}</span><span>${report.academic.year} · ${report.academic.term} · کلاس ${report.academic.className}</span>${report.demo && html`<em>نمونهٔ نمایشی</em>`}</div>
    <div class="analytical-sheet__grid">
      <${Panel} title="مشخصات دانش‌آموز" className="analytical-identity" tone="navy"><div class="report-portrait"><${Avatar} report=${report}/></div><dl class="report-identity-list"><div><dt>نام و نام خانوادگی</dt><dd>${report.student.name}</dd></div><div><dt>کد ملی</dt><dd>${report.student.nationalId}</dd></div><div><dt>شماره دانش‌آموزی</dt><dd>${report.student.number}</dd></div><div><dt>پایه و کلاس</dt><dd>${report.academic.grade} · ${report.academic.className}</dd></div></dl><div class="report-mini-kpis"><span><small>معدل کل</small><strong>${isNumber(report.average) ? fa(report.average) : '—'}</strong></span><span><small>رتبه کلاس</small><strong>${report.rank ? fa(report.rank) : '—'}</strong></span></div></${Panel}>
      <${Panel} title="نمودار روند رشد سه‌ساله" className="analytical-trend" action="میانگین و رتبه"><div class="trend-caption">مقایسهٔ میانگین نهایی سه سال اخیر</div>${loading ? html`<${Empty}/>` : html`<${EChart} option=${trend} label="نمودار روند تحصیلی سه‌ساله" className="echart--trend"/>`}${report.history?.length ? html`<div class="report-trend-foot">${report.history.map(item => html`<span><b>${item.label}</b><i>${fa(item.average)}</i>${item.rank ? html`<small>رتبه ${fa(item.rank)}</small>` : null}</span>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="گزارش مشاور" className="analytical-counselor" tone="gold">${report.counselor?.length ? html`<ul class="report-bullet-list">${report.counselor.map(item => html`<li>${item}</li>`)}</ul>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="پیگیری هوشمند" className="analytical-followups" tone="green">${report.followUps?.length ? html`<ul class="report-bullet-list">${report.followUps.map(item => html`<li>${item}</li>`)}</ul>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="وضعیت آموزشی و نمرات نهایی" className="analytical-table" tone="teal"><table class="report-score-table"><thead><tr><th>درس / شاخص</th><th>مستمر</th><th>میان‌ترم</th><th>پایانی</th><th>میانگین</th><th>وضعیت</th></tr></thead><tbody>${report.subjects.slice(0, 8).map(subject => html`<tr><th>${subject.title}</th><td>${fa(subject.continuous)}</td><td>${fa(subject.midterm)}</td><td>${fa(subject.final)}</td><td class=${subject.current < 12 ? 'is-alert' : 'is-current'}>${fa(subject.current)}</td><td>${subject.passed === false ? html`<b class="is-alert">پیگیری</b>` : html`<b class="is-ok">قبول</b>`}</td></tr>`)}</tbody></table>${!report.subjects?.length && html`<${Empty}/>`}</${Panel}>
      <${Panel} title="نمودار ارزیابی مهارت‌ها" className="analytical-radar" tone="teal">${radar ? html`<${EChart} option=${radar} label="نمودار راداری مهارت‌های تحصیلی" className="echart--radar"/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="گزارش تربیتی و رفتاری" className="analytical-behavior" tone="gold">${report.skills?.length ? html`<div class="report-rating-list">${report.skills.map(item => html`<div><span>${item.title}</span><${Stars} value=${item.value}/><b>${fa(item.value)}٪</b></div>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="نقاط قوت علمی" className="analytical-strengths" tone="green">${strengths ? html`<${EChart} option=${strengths} label="نقاط قوت علمی" className="echart--bars"/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="نقاط قابل بهبود" className="analytical-improvements" tone="rose">${improvements ? html`<${EChart} option=${improvements} label="نقاط قابل بهبود" className="echart--bars"/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="توصیه برای والدین" className="analytical-advice" tone="gold">${report.recommendations?.length ? html`<ol class="report-advice-list">${report.recommendations.map(item => html`<li>${item}</li>`)}</ol>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="توصیه برای معلمان" className="analytical-teacher" tone="navy">${report.teacherRecommendations?.length ? html`<ul class="report-bullet-list">${report.teacherRecommendations.map(item => html`<li>${item}</li>`)}</ul>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="حضور و غیاب" className="analytical-attendance" tone="navy"><div class="attendance-score"><strong>${attendanceRate === null ? '—' : `${fa(attendanceRate)}٪`}</strong><span>درصد حضور ثبت‌شده</span></div><div class="attendance-meta"><span>جلسات نهایی <b>${fa(report.attendance.sessions)}</b></span><span>غیبت غیرموجه <b>${fa(report.attendance.unexcused)}</b></span><span>تأخیر <b>${fa(report.attendance.late)}</b></span></div></${Panel}>
      <${Panel} title="مهارت‌های قرن بیست‌ویکم" className="analytical-skills21" tone="teal">${report.skills21?.length ? html`<div class="report-rating-list">${report.skills21.map(item => html`<div><span>${item.title}</span><${Stars} value=${item.value}/><b>${fa(item.value)}٪</b></div>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="مشارکت‌ها و فعالیت‌های مدرسه" className="analytical-activities" tone="teal">${report.activities?.length ? html`<div class="report-activities">${report.activities.map(item => html`<div><i>${item.icon}</i><strong>${item.title}</strong><small>${item.text}</small></div>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="آمادگی برای دوره متوسطه" className="analytical-readiness" tone="navy">${readiness ? html`<${EChart} option=${readiness} label="آمادگی تحصیلی برای دوره متوسطه" className="echart--readiness"/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="توصیهٔ ویژه و حمایت خانواده" className="analytical-support" tone="gold">${report.support?.length ? html`<ul class="report-bullet-list">${report.support.map(item => html`<li>${item}</li>`)}</ul>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="افتخارات و عناوین کسب‌شده" className="analytical-awards" tone="gold">${report.awards?.length ? html`<div class="report-awards">${report.awards.map(item => html`<div><i>${item.icon}</i><span><b>${item.title}</b><small>${item.text}</small></span></div>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="دسترسی سریع والدین" className="analytical-access" tone="navy"><div class="report-access"><${QrCode}/><strong>مشاهدهٔ نسخهٔ کامل</strong><small>${report.accessCode}</small></div></${Panel}>
    </div>
    <footer class="analytical-sheet__footer"><div><strong>این کارنامه صرفاً گزارش نمرات نیست.</strong><span>تصویری از مسیر رشد علمی، تربیتی و شخصیتی دانش‌آموز است.</span></div><div class="report-signatures"><span>امضای دبیر</span><span>معاون آموزشی</span><span>مدیر و مهر مدرسه</span></div><div><b>${report.school}</b><span>نسخهٔ تحلیلی · قابل مشاهده در سامانه و PDF رسمی</span></div></footer>
  </article>`;
}
