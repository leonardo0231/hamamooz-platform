import { html, useMemo } from '../core/view.js';
import { EChart } from './echart.js';
import { Icon } from './icons.js';

const fa = value => value === null || value === undefined || value === '' || !Number.isFinite(Number(value))
  ? '—'
  : new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(Number(value));
const clamp = (value, min = 0, max = 100) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.max(min, Math.min(max, numeric)) : null;
};
const isNumber = value => {
  if (typeof value !== 'number' && typeof value !== 'string') return false;
  if (typeof value === 'string' && value.trim() === '') return false;
  return Number.isFinite(Number(value));
};
const reportNumber = value => html`<bdi class="report-number" dir="ltr">${fa(value)}</bdi>`;
const bounded = (items, limit) => {
  const source = Array.isArray(items) ? items : [];
  return { items: source.slice(0, limit), omitted: Math.max(0, source.length - limit) };
};
const DEFAULT_STUDENT_PHOTO_URL = '/assets/report-default-student.svg';
const MONTH_TITLES = Object.freeze({
  1: 'تیر', 2: 'مرداد', 3: 'شهریور', 4: 'مهر', 5: 'آبان', 6: 'آذر',
  7: 'دی', 8: 'بهمن', 9: 'اسفند', 10: 'فروردین', 11: 'اردیبهشت', 12: 'خرداد',
});
const assetUrl = value => {
  if (!value) return '';
  const text = String(value).trim();
  if (/^(?:data:|blob:|file:|https?:\/\/|\/)/i.test(text)) return text;
  return `/${text}`;
};
const hasOwn = (value, key) => Boolean(value && Object.prototype.hasOwnProperty.call(value, key));
const rawMetricValue = item => {
  if (!item || typeof item !== 'object') return null;
  if (hasOwn(item, 'raw_score')) return item.raw_score;
  if (hasOwn(item, 'raw_value')) return item.raw_value;
  if (hasOwn(item, 'value')) return item.value;
  return null;
};
const rawMetricDisplay = value => {
  if (value === null || value === undefined || value === '') return 'ثبت نشده';
  if (typeof value === 'number' && Number.isFinite(value)) return fa(value);
  return String(value);
};
const numericOrNull = value => isNumber(value) ? Number(value) : null;

/**
 * Print the report that is already rendered by the React tree.  The print
 * stylesheet isolates the A3 report sheet from the application chrome, so the
 * browser is the only document renderer involved in the final output.
 */
export function printAnalyticalReport() {
  if (typeof window === 'undefined' || typeof window.print !== 'function') return false;
  const body = document.body;
  let printStarted = false;
  let printFallbackTimer;
  let cleanupTimer;
  const startPrint = () => {
    if (printStarted) return;
    printStarted = true;
    if (printFallbackTimer) window.clearTimeout(printFallbackTimer);
    window.print();
  };
  const cleanup = () => {
    body.classList.remove('report-printing');
    if (cleanupTimer) window.clearTimeout(cleanupTimer);
    if (printFallbackTimer) window.clearTimeout(printFallbackTimer);
  };
  body.classList.add('report-printing');
  window.addEventListener('afterprint', cleanup, { once: true });
  // Printing before the webfont or portrait has decoded is the most common
  // source of clipped Persian text and distorted student photos.  The report
  // is already in the DOM; wait for those assets, then let the browser open
  // its native print dialog.  A timeout keeps the print class from sticking
  // if a browser does not emit `afterprint` (for example, an embedded webview).
  const assets = [];
  if (document.fonts?.ready) assets.push(document.fonts.ready.catch(() => undefined));
  [...document.images].forEach(image => {
    if (image.complete) {
      assets.push(Promise.resolve());
      return;
    }
    assets.push(new Promise(resolve => {
      image.addEventListener('load', resolve, { once: true });
      image.addEventListener('error', resolve, { once: true });
    }));
  });
  // If an image server never answers, do not leave the user with a button that
  // appears to do nothing.  The browser still prints the explicit fallback
  // state for that image; successful loads normally reach this path earlier.
  printFallbackTimer = window.setTimeout(startPrint, 10000);
  cleanupTimer = window.setTimeout(() => {
    startPrint();
    window.setTimeout(cleanup, 5000);
  }, 30000);
  Promise.all(assets).finally(() => {
    window.setTimeout(startPrint, 120);
  });
  return true;
}

// Keep the browser report aligned with the nine domains used by the
// evaluation service.  A missing domain remains visible as “ثبت نشده” rather
// than silently disappearing from the radar or the availability strip.
export const ANALYSIS_DOMAINS = Object.freeze([
  { code: 'EDU', title: 'آموزشی' },
  { code: 'DEV', title: 'پرورشی' },
  { code: 'CHR', title: 'تربیتی' },
  { code: 'DIS', title: 'انضباطی' },
  { code: 'CUL', title: 'فرهنگی' },
  { code: 'RES', title: 'پژوهشی' },
  { code: 'SPT', title: 'ورزشی' },
  { code: 'ART', title: 'هنری' },
  { code: 'PER', title: 'مهارت‌های فردی' },
]);

// A single outline icon family keeps stickers legible in print and avoids
// emoji glyphs changing between operating systems and PDF engines.
export const REPORT_STICKER_ICONS = Object.freeze({
  sport: 'dumbbell', research: 'microscope', competition: 'trophy',
  cultural: 'bookOpen', art: 'palette', discipline: 'shieldCheck', activity: 'sparkles',
});

const metricTitles = {
  EDU_01: 'نمرات درسی', EDU_02: 'پیشرفت نسبت به قبل', EDU_03: 'انجام تکالیف', EDU_04: 'مشارکت در کلاس', EDU_05: 'دقت و تمرکز',
  DEV_01: 'احترام و همکاری', DEV_02: 'مسئولیت‌پذیری', DEV_04: 'نظم شخصی', DEV_10: 'اعتماد به نفس',
  CHR_01: 'خودکنترلی', CHR_02: 'انگیزه برای یادگیری', CHR_03: 'پشتکار', CHR_08: 'مدیریت استرس',
  DIS_01: 'حضور و غیاب', DIS_03: 'رعایت قوانین', PER_01: 'مدیریت زمان', PER_02: 'مهارت ارتباطی',
  PER_04: 'کار تیمی', PER_05: 'تفکر انتقادی',
};

const DEFAULT_SIGNATURE_LABELS = Object.freeze([
  'ولی دانش‌آموز',
  'مشاور',
  'دبیر راهنما',
  'معاون آموزشی',
  'مدیر مدرسه',
]);
const DEFAULT_REPORT_GRADE_RANGE = 'پایه هفتم تا نهم';

const demo = {
  demo: true,
  reportMode: 'official_term',
  reportTitle: 'کارنامه جامع رشد سه ساله دانش‌آموز',
  organization: 'سامانه هوشمند هم‌آموز',
  school: 'دبیرستان پسرانه بعثت',
  schoolLogoUrl: '/assets/besat-logo.png',
  student: { name: 'آرین محمدی', nationalId: '۰۰۱۲۳۴۵۶۷۸', number: '۹۹-۲۰۲۴', initial: 'آ', photoUrl: '' },
  academic: { year: '۱۴۰۴–۱۴۰۵', grade: 'پایه نهم', gradeRange: DEFAULT_REPORT_GRADE_RANGE, className: 'نهم / الف', term: 'نوبت اول' },
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
  domainScores: ANALYSIS_DOMAINS.map((domain, index) => ({
    ...domain,
    value: [90, 87, 85, 82, 78, 88, 92, 76, 84][index],
    percent: [90, 87, 85, 82, 78, 88, 92, 76, 84][index],
    completedMetrics: 4,
    totalMetrics: 4,
    hasData: true,
  })),
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
    { icon: 'competition', title: 'المپیاد علمی', text: 'مقام دوم منطقه' }, { icon: 'sport', title: 'مسابقات ورزشی', text: 'عضو تیم مدرسه' },
    { icon: 'research', title: 'پژوهش و تحلیل', text: 'پروژه برگزیده' }, { icon: 'cultural', title: 'باشگاه کتاب‌خوانی', text: 'مشارکت مستمر' },
  ],
  awards: [{ icon: 'competition', title: 'المپیاد علمی', text: 'مقام دوم منطقه' }, { icon: 'discipline', title: 'دانش‌آموز منظم', text: 'نوبت اول ۱۴۰۴' }, { icon: 'research', title: 'پژوهش برتر', text: 'نمایشگاه مدرسه' }],
  counselor: ['روند پیشرفت در سه سال پایدار و رو به رشد است.', 'اعتماد به نفس در ارائه‌های کلاسی تقویت شود.', 'برای مدیریت زمان، برنامه هفتگی مشترک تنظیم شود.'],
  recommendations: ['برنامه ثابت مطالعه روزانه برای تثبیت رشد ادامه یابد.', 'در پروژه‌های پژوهشی و کارگروهی نقش ارائه‌دهنده تجربه شود.'],
  teacherRecommendations: ['تمرین‌های چالشی ریاضی به‌صورت هفتگی پیگیری شود.', 'بازخورد کوتاه و مشخص پس از ارائه‌های کلاسی ارائه شود.'],
  followUps: ['پیگیری منظم تکالیف و پروژه‌ها', 'تقویت مهارت ارائه در فعالیت‌های کلاسی', 'مشارکت بیشتر در گروه‌های پژوهشی'],
  support: ['همراهی خانواده در مرور برنامه هفتگی', 'گفت‌وگوی کوتاه ماهانه با مشاور مدرسه'],
  signatures: DEFAULT_SIGNATURE_LABELS,
  attendance: { rate: 96, sessions: 42, unexcused: 1, late: 2 },
};

// A real but empty snapshot must never be replaced with fictional demo data.
// This state keeps the report shell printable while making every unavailable
// field explicit for the school operator.
const emptyReport = {
  demo: false,
  reportMode: 'official_term',
  reportTitle: 'کارنامه جامع رشد سه ساله دانش‌آموز',
  organization: 'ثبت نشده',
  school: 'ثبت نشده',
  schoolLogoUrl: '',
  student: { name: 'ثبت نشده', nationalId: '—', number: '—', initial: 'د', photoUrl: '' },
  academic: { year: '—', grade: '—', gradeRange: DEFAULT_REPORT_GRADE_RANGE, className: '—', term: '—' },
  average: null,
  rank: null,
  history: [],
  subjects: [],
  skills: [],
  skills21: [],
  readiness: [],
  domainScores: ANALYSIS_DOMAINS.map(domain => ({ ...domain, value: null, percent: null, completedMetrics: 0, totalMetrics: 0, hasData: false })),
  strengths: [],
  improvements: [],
  activities: [],
  awards: [],
  counselor: [],
  recommendations: [],
  teacherRecommendations: [],
  followUps: [],
  support: [],
  signatures: DEFAULT_SIGNATURE_LABELS,
  attendance: { rate: null, sessions: null, unexcused: null, late: null },
  completionPercent: null,
  completionStatus: 'provisional',
  monthlyChange: null,
  monthlyChanges: [],
  monthlyScores: [],
  metricRows: [],
  missingSections: [],
  subjectsOmitted: 0, strengthsOmitted: 0, improvementsOmitted: 0,
  skillsOmitted: 0, skills21Omitted: 0, activitiesOmitted: 0, awardsOmitted: 0,
  counselorOmitted: 0, followUpsOmitted: 0, recommendationsOmitted: 0,
  teacherRecommendationsOmitted: 0, supportOmitted: 0,
};

function titleForMetric(code) { return metricTitles[code] ?? String(code || '').replace('_', ' '); }
function normalizeSignatureLabels(value) {
  const source = Array.isArray(value) && value.length ? value : DEFAULT_SIGNATURE_LABELS;
  return source.map(item => typeof item === 'string' ? item : item?.title ?? item?.label ?? item?.role).filter(Boolean).slice(0, 5);
}
function metricValue(value) {
  // MonthlyEvaluation/MetricScore is an explicit 0–5 integer rubric.  Do not
  // infer a unit from the magnitude: EDU_01 in the source workbooks is a
  // 0–20 academic score, while EDU_02 can be decimal, negative, or «ندارد».
  // Those values are not this rubric and must remain unavailable until the
  // school approves a mapping.
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || !Number.isInteger(numeric) || numeric < 0 || numeric > 5) return null;
  return numeric * 20;
}
function numericSubject(row) {
  const value = isNumber(row) ? Number(row) : isNumber(row?.average) ? Number(row.average) : null;
  // Academic subjects are already on the official 0–20 scale.  Reject an
  // out-of-range value instead of allowing a later percentage clamp to turn
  // a corrupt negative score into a visible zero.
  return value !== null && value >= 0 && value <= 20 ? value : null;
}

function metricDomainCode(item) {
  return String(item?.domain_code ?? item?.domainCode ?? item?.code ?? '')
    .split('_', 1)[0]
    .toUpperCase();
}

function normalizeMetricRow(item) {
  const source = item && typeof item === 'object' ? item : {};
  const code = source.code ?? source.metric_code;
  const rawValue = rawMetricValue(source);
  const value = metricValue(rawValue);
  return {
    ...source,
    code,
    title: source.title ?? titleForMetric(code),
    rawValue,
    value,
    hasData: value !== null,
  };
}

function domainPercent(item) {
  if (!item || item.has_data === false || item.hasData === false) return null;
  if (isNumber(item.score)) {
    const score = Number(item.score);
    return score >= 0 && score <= 20 ? score * 5 : null;
  }
  if (isNumber(item.percent)) {
    const percent = Number(item.percent);
    return percent >= 0 && percent <= 100 ? percent : null;
  }
  // A bare `value` is ambiguous (it may be a 0–20 score or a percentage).
  // Only accept it when the producer declares its unit/scale explicitly;
  // otherwise keeping the domain missing is safer than silently converting it.
  if (isNumber(item.value)) {
    const value = Number(item.value);
    const unit = String(item.value_unit ?? item.unit ?? item.scale ?? '').trim().toLowerCase();
    if (['percent', 'percentage', '%', 'درصد'].includes(unit)) {
      return value >= 0 && value <= 100 ? value : null;
    }
    if (['score_20', '0-20', '20'].includes(unit)) {
      return value >= 0 && value <= 20 ? value * 5 : null;
    }
  }
  return null;
}

// Export the boundary normalizers so the React report contract can be tested
// without mounting a browser document.  They intentionally return null for
// values whose unit or range is not authoritative.
export {
  metricValue as normalizeReportMetricValue,
  numericSubject as normalizeReportSubjectScore,
  domainPercent as normalizeReportDomainPercent,
  normalizeDomainScores as normalizeReportDomainScores,
};

function normalizeDomainScores(rows, metricRows = []) {
  const sourceRows = Array.isArray(rows) ? rows : [];
  const rowByCode = new Map(sourceRows.map(item => [
    String(item?.code ?? item?.domain_code ?? '').toUpperCase(), item,
  ]));
  const metricGroups = new Map();
  for (const item of metricRows) {
    const code = metricDomainCode(item);
    if (!code) continue;
    // mapSnapshot has already converted valid rubric scores to percentages;
    // applying metricValue a second time would discard every value above 5.
    const value = item.hasData === false || !isNumber(item.value)
      ? null
      : Number(item.value) >= 0 && Number(item.value) <= 100 ? Number(item.value) : null;
    if (value !== null) metricGroups.set(code, [...(metricGroups.get(code) ?? []), value]);
  }
  return ANALYSIS_DOMAINS.map(domain => {
    const source = rowByCode.get(domain.code);
    const values = metricGroups.get(domain.code) ?? [];
    const value = source
      ? domainPercent(source)
      : values.length ? clamp(values.reduce((sum, item) => sum + item, 0) / values.length) : null;
    const completedMetrics = source?.completed_metrics ?? source?.completedMetrics
      ?? (values.length || value === null ? values.length : 1);
    return {
      ...domain,
      ...source,
      title: source?.title ?? source?.domain_title ?? domain.title,
      value,
      percent: value,
      completedMetrics,
      totalMetrics: source?.total_metrics ?? source?.totalMetrics ?? 0,
      hasData: value !== null,
    };
  });
}

function mapDataMonthlyReport(report) {
  // ``monthly-preview`` is deliberately a separate API contract: it has no
  // official term or subject grades.  Adapt it here, at the React boundary,
  // instead of making the backend invent fields from an official report.
  const rawMetrics = Array.isArray(report?.metrics) ? report.metrics : [];
  // Keep every coded metric row, including an invalid/raw value such as
  // «ندارد».  The table uses rawValue for auditability while value is only the
  // authoritative 0–5 rubric converted to a percentage.
  const metricRows = rawMetrics.map(normalizeMetricRow).filter(item => item.code);
  const behavior = metricRows.filter(item => /^(DEV|CHR|DIS)_/.test(item.code ?? ''));
  const skills21 = metricRows.filter(item => /^PER_/.test(item.code ?? ''));
  const indexRows = metricRows.filter(item => /^(EDU|DEV|CHR|DIS)_/.test(item.code ?? ''));
  const domainScores = normalizeDomainScores(report?.domains, metricRows);
  const metricInsights = indexRows
    .filter(item => item.hasData && isNumber(item.value))
    .map(item => ({ code: item.code, title: item.title, value: Number(item.value) }));
  const externalMetricInsights = rows => (Array.isArray(rows) ? rows : [])
    .filter(item => /_/.test(String(item?.code ?? item?.metric_code ?? '')))
    .map(item => ({
      code: item.code ?? item.metric_code,
      title: item.title ?? item.domain_title ?? item.code ?? 'ثبت نشده',
      value: domainPercent(item),
    }))
    .filter(item => isNumber(item.value));
  const insightSource = metricInsights.length ? metricInsights : externalMetricInsights(report?.strengths);
  const strengths = bounded([...insightSource].sort((a, b) => b.value - a.value), 6);
  const improvements = bounded([...insightSource].sort((a, b) => a.value - b.value), 6);
  const recommendations = bounded((report?.recommendations ?? [])
    .map(item => typeof item === 'string' ? item : item?.text ?? item?.title)
    .filter(Boolean), 6);
  const student = report?.student ?? {};
  const month = report?.month ?? {};
  const overallScore = numericSubject(report?.overall_score);
  const monthlyChanges = Array.isArray(report?.monthly_changes) ? report.monthly_changes : [];
  const currentMonthNo = numericOrNull(month.no);
  const history = (Array.isArray(report?.monthly_scores) ? report.monthly_scores : [])
    .map(item => {
      const average = numericSubject(item?.overall_score ?? item?.average);
      if (average === null) return null;
      const monthNo = numericOrNull(item?.month_no);
      return {
        label: item?.month_title ?? item?.title ?? (monthNo === currentMonthNo ? month.title : null) ?? (monthNo === null ? 'ماه ثبت‌شده' : MONTH_TITLES[monthNo] ?? `ماه ${fa(monthNo)}`),
        average,
        rank: null,
        monthNo,
      };
    })
    .filter(Boolean);
  if (overallScore !== null && !history.some(item => item.monthNo !== null && item.monthNo === currentMonthNo)) {
    history.push({ label: month.title ?? 'ماه جاری', average: overallScore, rank: null, monthNo: currentMonthNo });
  }
  const declaredChange = numericOrNull(report?.monthly_change);
  const currentChange = declaredChange ?? numericOrNull(monthlyChanges.find(item => numericOrNull(item?.to_month_no) === currentMonthNo)?.change);
  const organizationSource = typeof report?.organization === 'object' ? report.organization : {};
  const schoolSource = typeof report?.school === 'object' ? report.school : {};
  const fallbackOrganization = typeof report?.organization === 'string' ? report.organization : 'ثبت نشده';
  const fallbackSchool = typeof report?.school === 'string' ? report.school : 'ثبت نشده';
  const summerTitle = 'کارنامه ارزیابی تابستانه رشد دانش‌آموز';
  const requestedTitle = typeof report?.title === 'string' ? report.title.trim() : '';
  const reportTitle = requestedTitle && !/سه\s*ساله/.test(requestedTitle) ? requestedTitle : summerTitle;
  const sourceSections = Array.isArray(report?.missing_sections) ? report.missing_sections : [];
  return {
    demo: false,
    reportMode: 'data_monthly',
    reportTitle,
    organization: organizationSource.name ?? fallbackOrganization,
    school: schoolSource.name ?? fallbackSchool,
    schoolLogoUrl: assetUrl(schoolSource.logo_url || organizationSource.logo_url || report?.school_logo_url),
    student: {
      name: student.name ?? 'ثبت نشده',
      nationalId: student.national_id ?? '—',
      number: student.student_number ?? '—',
      initial: (student.name ?? 'د').slice(0, 1),
      photoUrl: assetUrl(student.photo_url),
    },
    academic: {
      year: report?.academic?.year ?? '—', grade: student.grade ?? 'ثبت نشده', gradeRange: student.grade ?? DEFAULT_REPORT_GRADE_RANGE,
      className: student.class_code ?? 'ثبت نشده',
      term: month.title ? `${month.title} · گزارش ماهانه` : 'گزارش ماهانه',
    },
    average: overallScore,
    rank: null,
    history,
    subjects: [],
    skills: behavior,
    skills21,
    readiness: [],
    domainScores,
    strengths: strengths.items,
    improvements: improvements.items,
    activities: [],
    awards: [],
    counselor: [],
    recommendations: recommendations.items,
    teacherRecommendations: [],
    followUps: [],
    support: [],
    signatures: DEFAULT_SIGNATURE_LABELS,
    attendance: { rate: null, sessions: null, unexcused: null, late: null },
    completionPercent: clamp(report?.completion_percent),
    completionStatus: report?.completion_status ?? 'provisional',
    monthlyChange: currentChange,
    monthlyChanges,
    monthlyScores: history,
    monthlyHistory: history,
    metricRows,
    indexRows,
    sourceFile: report?.source_file ?? '',
    sourceRow: report?.source_row ?? null,
    missingSections: sourceSections,
    subjectsOmitted: 0,
    strengthsOmitted: strengths.omitted,
    improvementsOmitted: improvements.omitted,
    skillsOmitted: 0,
    skills21Omitted: 0,
    activitiesOmitted: 0,
    awardsOmitted: 0,
    counselorOmitted: 0,
    followUpsOmitted: 0,
    recommendationsOmitted: recommendations.omitted,
    teacherRecommendationsOmitted: 0,
    supportOmitted: 0,
  };
}

export function mapSnapshot(snapshot) {
  if (snapshot?.report_mode === 'data_monthly') return mapDataMonthlyReport(snapshot);
  const report = snapshot?.reports?.[0];
  if (report?.report_mode === 'data_monthly') return mapDataMonthlyReport(report);
  if (!report) return snapshot === undefined || snapshot === null ? demo : { ...emptyReport };
  const context = report.product_context ?? {};
  const latest = context.evaluations?.at?.(-1);
  // Some older snapshots emitted both fields but left `metrics` empty.  Use
  // the populated representation first so a sparse array cannot hide the
  // persisted metric-score map.
  const rawMetrics = latest?.metrics?.length ? latest.metrics : latest?.metric_scores ?? [];
  const metrics = Array.isArray(rawMetrics)
    ? rawMetrics
    : Object.entries(rawMetrics).map(([code, value]) => ({ code, title: titleForMetric(code), value }));
  const metricRows = metrics.map(normalizeMetricRow).filter(item => item.code);
  const behavior = metricRows.filter(item => /^(DEV|CHR|DIS)_/.test(item.code ?? ''));
  const skills21 = metricRows.filter(item => /^PER_/.test(item.code ?? ''));
  const subjectRows = (report.subjects ?? []).map(item => ({
    title: item.title ?? 'درس / شاخص ثبت نشده', current: numericSubject(item), first: numericSubject(item.first), previous: numericSubject(item.previous),
    continuous: numericSubject(item.continuous), midterm: numericSubject(item.midterm), final: numericSubject(item.final), passed: item.passed,
  }));
  const history = (report.history ?? []).map(item => {
    const average = numericSubject(item?.average);
    return average === null ? null : { label: item.label, average, rank: item.rank ?? null };
  }).filter(Boolean);
  const historyGradeRange = history.length > 1 ? `${history[0].label} تا ${history.at(-1).label}` : null;
  const reportTitle = [report.report_title, report.title, context.report_title].find(value => typeof value === 'string' && value.trim())
    ?? 'کارنامه جامع رشد سه ساله دانش‌آموز';
  const gradeRange = report.academic?.grade_range ?? report.academic?.gradeRange ?? historyGradeRange ?? DEFAULT_REPORT_GRADE_RANGE;
  const academic = metricRows.filter(item => /^EDU_/.test(item.code ?? ''));
  const visibleSubjects = bounded(subjectRows, 12);
  const strengthRows = [...subjectRows].filter(item => isNumber(item.current)).sort((a, b) => b.current - a.current).map(item => ({ title: item.title, value: clamp(item.current * 5) }));
  const improvementRows = [...subjectRows].filter(item => isNumber(item.current)).sort((a, b) => a.current - b.current).map(item => ({ title: item.title, value: clamp(item.current * 5) }));
  const strengths = bounded(strengthRows, 6);
  const improvements = bounded(improvementRows, 6);
  const attendance = context.attendance ?? {};
  const attendanceRate = isNumber(attendance.attendance_rate) ? Number(attendance.attendance_rate) : isNumber(attendance.present_rate) ? Number(attendance.present_rate) : null;
  const recommendations = context.approved_recommendations ?? [];
  const domainScores = normalizeDomainScores(context.evaluation_analysis?.domain_scores, metricRows);
  const allActivities = (context.activities ?? []).map(item => ({
    icon: REPORT_STICKER_ICONS[item.kind] ? item.kind : 'activity',
    title: item.title, text: item.result || (item.placement ? `رتبه ${fa(item.placement)}` : 'ثبت‌شده'),
  }));
  const activities = bounded(allActivities, 8);
  const awards = bounded(allActivities.filter(item => item.text !== 'ثبت‌شده'), 4);
  const organization = typeof report.organization === 'object' ? report.organization : {};
  const recommendationText = item => typeof item === 'string' ? item : item?.approved_text;
  const allParentRecommendations = recommendations
    .filter(item => typeof item === 'string' || !item.audience || ['parent', 'student'].includes(item.audience))
    .map(recommendationText).filter(Boolean);
  const parentRecommendations = bounded(allParentRecommendations, 6);
  const allSupportNotes = (context.support_notes ?? [])
    .map(item => typeof item === 'string' ? item : item?.text).filter(Boolean);
  const supportNotes = bounded(allSupportNotes, 3);
  const allCounselor = (context.counselor_report?.items ?? context.analytics_signals ?? [])
    .map(item => typeof item === 'string' ? item : item.explanation).filter(Boolean);
  const allTeacherRecommendations = recommendations
    .filter(item => item?.audience && ['teacher', 'guide_teacher', 'educational_deputy'].includes(item.audience))
    .map(recommendationText).filter(Boolean);
  const allFollowUps = (context.analytics_signals ?? [])
    .map(item => item.explanation).filter(Boolean);
  const counselor = bounded(allCounselor, 4);
  const teacherRecommendations = bounded(allTeacherRecommendations, 6);
  const followUps = bounded(allFollowUps, 4);
  const signatures = normalizeSignatureLabels(report.signatures ?? context.signatures);
  return {
    demo: false, reportMode: 'official_term', reportTitle, organization: organization.name ?? (typeof report.organization === 'string' ? report.organization : 'سامانه هم‌آموز'), school: report.school?.name ?? 'مدرسه',
    schoolLogoUrl: assetUrl(report.school?.logo_url || organization.logo_url || context.school_logo_url),
    student: { name: report.student?.full_name ?? 'دانش‌آموز', nationalId: report.student?.national_id ?? '—', number: report.student?.student_number ?? '—', initial: (report.student?.full_name ?? 'د').slice(0, 1), photoUrl: assetUrl(report.student?.photo_url || report.student?.photo) },
    academic: { year: report.academic?.year ?? '—', grade: report.academic?.grade ?? '—', gradeRange, className: report.academic?.class ?? '—', term: report.academic?.term ?? '—' },
    average: numericSubject(report.summary?.average), rank: report.summary?.class_rank ?? null, history,
    subjects: visibleSubjects.items, skills: behavior, skills21, readiness: academic, domainScores,
    strengths: strengths.items, improvements: improvements.items, activities: activities.items, awards: awards.items,
    counselor: counselor.items,
    recommendations: parentRecommendations.items,
    teacherRecommendations: teacherRecommendations.items,
    followUps: followUps.items,
    // Keep family-support evidence separate from parent/student advice.  If
    // the backend has no support note, the report must say so explicitly
    // instead of presenting a duplicated recommendation as a fact.
    support: supportNotes.items,
    signatures,
    attendance: { rate: attendanceRate, sessions: attendance.finalized_session_count ?? null, unexcused: attendance.unexcused_absence_count ?? null, late: attendance.late_count ?? null },
    completionPercent: null,
    completionStatus: 'final',
    monthlyChange: null,
    monthlyChanges: [],
    monthlyScores: [],
    metricRows,
    indexRows: academic,
    missingSections: [],
    subjectsOmitted: visibleSubjects.omitted, strengthsOmitted: Math.max(0, strengthRows.length - strengths.items.length),
    improvementsOmitted: Math.max(0, improvementRows.length - improvements.items.length), skillsOmitted: 0,
    skills21Omitted: 0, activitiesOmitted: activities.omitted, awardsOmitted: awards.omitted,
    counselorOmitted: counselor.omitted, followUpsOmitted: followUps.omitted,
    recommendationsOmitted: parentRecommendations.omitted, teacherRecommendationsOmitted: teacherRecommendations.omitted,
    supportOmitted: supportNotes.omitted,
  };
}

function trendOption(points) {
  if (!points?.length) return null;
  const values = points.map(item => Number(item.average)).filter(value => Number.isFinite(value));
  const minValue = values.length ? Math.min(...values) : 0;
  const maxValue = values.length ? Math.max(...values) : 20;
  const min = Math.max(0, Math.floor(minValue - 1));
  const max = Math.min(20, Math.max(min + 4, Math.ceil(maxValue + 1)));
  return { color: ['#0f766e'], textStyle: { fontFamily: 'Vazirmatn' }, tooltip: { trigger: 'axis', confine: true, valueFormatter: value => `${fa(value)} از ۲۰` }, grid: { top: 24, right: 12, bottom: 38, left: 32 },
    xAxis: { type: 'category', data: points.map(item => shortTrendLabel(item.label)), axisTick: { show: false }, axisLine: { lineStyle: { color: '#cbd5e1' } }, axisLabel: { color: '#475569', fontSize: 11, fontFamily: 'Vazirmatn', interval: 0, margin: 12, hideOverlap: true } },
    yAxis: { type: 'value', min, max, splitNumber: 4, axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Vazirmatn' }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } },
    series: [{ name: 'میانگین', type: 'line', smooth: true, data: points.map(item => item.average), symbolSize: 9, lineStyle: { width: 4 }, areaStyle: { color: 'rgba(15,118,110,.16)' }, itemStyle: { borderColor: '#fff', borderWidth: 2 } }],
  };
}

function shortTrendLabel(label) { return String(label || '').replace(/^پایه\s*/, ''); }

function radarOption(items) {
  if (!items?.length) return null;
  const radarItems = items.filter(Boolean);
  return { textStyle: { fontFamily: 'Vazirmatn' }, tooltip: { confine: true }, radar: { radius: '39%', center: ['50%', '47%'], axisNameGap: 8, indicator: radarItems.map((item, index) => ({ name: String(index + 1), title: item.title, max: 100 })), splitNumber: 4, splitArea: { areaStyle: { color: ['#fff', '#f2faf8'] } }, axisName: { color: 'transparent', fontSize: 12, fontWeight: 900, fontFamily: 'Vazirmatn', formatter: () => '' }, splitLine: { lineStyle: { color: '#cbd5e1' } }, axisLine: { lineStyle: { color: '#dbeafe' } } },
    series: [{ type: 'radar', symbol: 'circle', symbolSize: 7, data: [{ value: radarItems.map(item => item.hasData === false ? null : item.value), name: 'ارزیابی مهارت‌ها', areaStyle: { color: 'rgba(14,116,144,.22)' }, lineStyle: { color: '#0e7490', width: 2.5 }, itemStyle: { color: '#0e7490' } }] }],
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
  return html`<section class=${`analytical-panel analytical-panel--${tone} ${className}`}><header class="analytical-panel__header"><h3>${displayTitle}</h3>${action && html`<span>${action}</span>`}</header><div class="analytical-panel__body">${children}</div></section>`;
}
function Empty({ message = 'داده کافی نیست' }) { return html`<p class="analytical-empty">${message}</p>`; }
function OverflowNote({ count }) {
  if (!count) return null;
  return html`<p class="report-overflow-note" role="note">${fa(count)} مورد دیگر در پروندهٔ کامل باقی مانده است.</p>`;
}
function Stars({ value }) {
  if (!isNumber(value)) return html`<span class="report-rating-missing" role="status" aria-label="امتیاز ثبت نشده">ثبت نشده</span>`;
  const rounded = Math.round(Number(value) / 20);
  return html`<span class="report-stars" aria-label=${`${fa(value)} درصد`}>${[1, 2, 3, 4, 5].map(index => html`<${Icon} key=${`star-${index}`} name="star" size=${15} className=${index <= rounded ? 'is-on' : ''}/>` )}</span>`;
}
function MetricPercent({ value }) {
  return isNumber(value)
    ? html`<span class="report-metric-percent">${reportNumber(value)}٪</span>`
    : html`<span class="report-rating-missing" role="status">ثبت نشده</span>`;
}
function SubjectStatus({ subject }) {
  if (subject.passed === true) return html`<b class="is-ok">قبول</b>`;
  if (subject.passed === false) return html`<b class="is-alert">پیگیری</b>`;
  return html`<span class="report-rating-missing" role="status">ثبت نشده</span>`;
}
function MissingPhoto() {
  return html`<span class="report-avatar-fallback" role="img" aria-label="تصویر پیش‌فرض دانش‌آموز"><img src=${DEFAULT_STUDENT_PHOTO_URL} alt="تصویر پیش‌فرض دانش‌آموز"/><small>تصویر پیش‌فرض</small></span>`;
}
function StudentPhoto({ report }) {
  if (!report.student.photoUrl) return html`<${MissingPhoto}/>`;
  return html`<span class="report-photo"><img src=${report.student.photoUrl} alt=${`عکس ${report.student.name}`} onError=${event => {
    event.currentTarget.hidden = true;
    event.currentTarget.parentElement?.querySelector('[data-photo-fallback]')?.removeAttribute('hidden');
  }}/><span class="report-avatar-fallback" data-photo-fallback hidden role="img" aria-label="تصویر پیش‌فرض دانش‌آموز"><img src=${DEFAULT_STUDENT_PHOTO_URL} alt="تصویر پیش‌فرض دانش‌آموز"/><small>تصویر پیش‌فرض</small></span></span>`;
}
function MissingLogo() {
  return html`<span class="report-logo-fallback" role="img" aria-label="لوگوی مدرسه ثبت نشده"><${Icon} name="school" size=${29}/><small>لوگو ثبت نشده</small></span>`;
}
function SchoolMark({ report }) {
  if (!report.schoolLogoUrl) return html`<${MissingLogo}/>`;
  return html`<span class="report-logo-frame"><img src=${report.schoolLogoUrl} alt="لوگوی مدرسه" onError=${event => {
    event.currentTarget.hidden = true;
    event.currentTarget.parentElement?.querySelector('[data-logo-fallback]')?.removeAttribute('hidden');
  }}/><span class="report-logo-fallback" data-logo-fallback hidden role="img" aria-label="لوگوی مدرسه در دسترس نیست"><${Icon} name="school" size=${29}/><small>لوگو در دسترس نیست</small></span></span>`;
}
function Sticker({ kind = 'activity', title }) {
  const icon = REPORT_STICKER_ICONS[kind] ? REPORT_STICKER_ICONS[kind] : REPORT_STICKER_ICONS.activity;
  return html`<span class=${`report-sticker report-sticker--${kind}`} role="img" aria-label=${`نشان ${title}`}><${Icon} name=${icon} size=${27}/></span>`;
}
function MetricAvailability({ report }) {
  const items = report.domainScores?.length ? report.domainScores : ANALYSIS_DOMAINS.map(domain => ({ ...domain, value: null, hasData: false, completedMetrics: 0 }));
  return html`<div class="analytical-analysis-strip" aria-label="وضعیت داده‌های تحلیلی">${items.map(item => {
    const available = item.hasData !== false && isNumber(item.value);
    const count = isNumber(item.completedMetrics) && Number(item.completedMetrics) > 0 ? Number(item.completedMetrics) : available ? 1 : 0;
    const status = available ? `${fa(count)} شاخص ثبت‌شده` : 'ثبت نشده';
    return html`<span class=${available ? 'is-available' : 'is-missing'} aria-label=${`${item.title}: ${status}`}><i aria-hidden="true"></i><b>${item.title}</b><small>${status}</small></span>`;
  })}</div>`;
}

function RecommendationGroup({ title, items, omitted = 0, ordered = false, tone = 'teal' }) {
  if (!items?.length) return html`<div class="report-recommendation-group report-recommendation-group--empty"><h4>${title}</h4><${Empty} message="توصیه‌ای ثبت نشده است"/></div>`;
  const List = ordered ? 'ol' : 'ul';
  return html`<div class=${`report-recommendation-group report-recommendation-group--${tone}`}><h4>${title}</h4><${List} class="report-bullet-list">${items.map(item => html`<li>${item}</li>`)}</${List}><${OverflowNote} count=${omitted}/></div>`;
}

function MissingSection({ message = 'اطلاعات ثبت نشده' }) {
  return html`<p class="analytical-empty report-missing-section" role="status">${message}</p>`;
}

function ReportFooter({ report, monthly = false }) {
  const heading = monthly ? 'توضیحات و امضا' : 'امضا و تأیید مسئولان مدرسه';
  const note = monthly
    ? 'این نسخه بر اساس شاخص‌های ثبت‌شده در ارزیابی ماهانه صادر شده است.'
    : 'این کارنامه تصویری جامع از مسیر رشد علمی، تربیتی و شخصیتی دانش‌آموز است.';
  return html`<footer class=${`analytical-sheet__footer ${monthly ? 'monthly-sheet__footer' : ''}`}>
    <div class="report-footer-signatures"><div class="report-signature-heading"><strong>${heading}</strong><span>${note}</span></div><div class="report-signatures">${report.signatures.map((label, index) => html`<span key=${`signature-${monthly ? 'monthly-' : ''}${index}`}>${label}</span>`)}</div></div>
    <div class="report-footer-note"><span>هم‌آموز</span><strong>${monthly ? 'گزارش رشد ماهانه' : 'گزارش جامع رشد دانش‌آموز'}</strong><p>${monthly ? 'اطلاعات ثبت‌نشده در این نسخه به‌عنوان داده‌ی در انتظار ثبت نمایش داده شده است.' : 'رشد هر دانش‌آموز، مسیر منحصربه‌فردی است که با همراهی مدرسه و خانواده کامل می‌شود.'}</p></div>
    <div class="report-footer-brand"><div class="report-footer-brand__mark"><${SchoolMark} report=${report}/></div><strong>${report.school}</strong><span>${report.organization}</span><small>برای رشد، یادگیری و ساختن آینده‌ای روشن</small></div>
  </footer>`;
}

function MonthlyMetricTable({ report }) {
  const rows = Array.isArray(report.indexRows) ? report.indexRows : [];
  if (!rows.length) return html`<${MissingSection}/>`;
  return html`<table class="report-score-table report-monthly-metric-table"><caption class="sr-only">شاخص‌های آموزشی و رفتاری</caption><thead><tr><th scope="col">شاخص</th><th scope="col">حوزه</th><th scope="col">مقدار خام</th><th scope="col">امتیاز</th><th scope="col">وضعیت</th></tr></thead><tbody>${rows.map(item => {
    const available = item.hasData && isNumber(item.value);
    const domain = ANALYSIS_DOMAINS.find(candidate => candidate.code === metricDomainCode(item));
    return html`<tr key=${item.code} class=${available ? 'is-available' : 'is-missing'}><th scope="row"><span class="report-score-table__subject">${item.title}</span><small class="report-metric-code" dir="ltr">${item.code}</small></th><td>${item.domain_title ?? domain?.title ?? 'ثبت نشده'}</td><td><bdi class="report-raw-value" dir="ltr">${rawMetricDisplay(item.rawValue)}</bdi></td><td>${available ? html`<${MetricPercent} value=${item.value}/>` : html`<span class="report-rating-missing">ثبت نشده</span>`}</td><td>${available ? html`<b class="is-ok">ثبت شده</b>` : html`<span class="report-rating-missing">ثبت نشده</span>`}</td></tr>`;
  })}</tbody></table>`;
}

function MonthlyChange({ report }) {
  const change = numericOrNull(report.monthlyChange);
  const changeClass = change === null ? 'is-missing' : change > 0 ? 'is-positive' : change < 0 ? 'is-negative' : 'is-stable';
  const label = change === null
    ? 'ثبت نشده'
    : change > 0
      ? `افزایش ${fa(change)} نمره`
      : change < 0
        ? `کاهش ${fa(Math.abs(change))} نمره`
        : 'بدون تغییر';
  const latest = report.monthlyHistory?.at?.(-1);
  const previous = report.monthlyHistory?.at?.(-2);
  return html`<div class=${`monthly-change ${changeClass}`}><span class="monthly-change__icon" aria-hidden="true">${change === null ? '—' : change > 0 ? '↑' : change < 0 ? '↓' : '→'}</span><div><strong>${label}</strong><small>${previous && latest ? `${previous.label} ← ${latest.label}` : 'مقایسه با ارزیابی قبلی'}</small></div></div>`;
}

function MonthlyReport({ report, loading = false }) {
  const trend = trendOption(report.monthlyHistory ?? report.history);
  const radar = radarOption(report.domainScores);
  const strengths = barsOption(report.strengths, '#0f766e');
  const improvements = barsOption(report.improvements, '#a61d4d');
  const completion = isNumber(report.completionPercent) ? clamp(report.completionPercent) : null;
  const average = isNumber(report.average) ? report.average : null;
  const statusLabel = report.completionStatus === 'final' ? 'تکمیل‌شده' : 'ناقص / در حال تکمیل';
  const sourceLabel = report.sourceFile
    ? `منبع: ${report.sourceFile}${report.sourceRow ? ` · ردیف ${fa(report.sourceRow)}` : ''}`
    : 'منبع دادهٔ ماهانه';
  return html`<article class="analytical-sheet analytical-sheet--monthly" data-report-mode="data_monthly" aria-label=${`کارنامه تابستانه ${report.student.name}`}>
    <header class="analytical-sheet__header monthly-sheet__header"><div class="analytical-sheet__mark"><${SchoolMark} report=${report}/></div><div class="analytical-sheet__heading"><p>${report.reportTitle}</p><h2>${report.academic.term}</h2><strong>${report.school}</strong></div><div class="monthly-sheet__meta"><strong>گزارش شاخص‌محور</strong><span>${report.organization}</span><span>${report.academic.grade} · کلاس ${report.academic.className}</span></div></header>
    <div class="analytical-sheet__subhead monthly-sheet__subhead"><span>ارزیابی تابستانه بر اساس داده‌های واقعی</span><span>${sourceLabel}</span></div>
    <div class="monthly-kpi-strip" aria-label="خلاصهٔ امتیاز و تکمیل گزارش"><div class="monthly-kpi"><span>امتیاز کلی</span><strong>${average === null ? 'ثبت نشده' : html`<span class="monthly-kpi-value">${reportNumber(average)} <small>از ۲۰</small></span>`}</strong><em>${report.completionStatus === 'final' ? 'ارزیابی نهایی' : 'ارزیابی موقت'}</em></div><div class="monthly-kpi monthly-kpi--completion"><span>درصد تکمیل داده</span><strong>${completion === null ? 'ثبت نشده' : html`<span class="monthly-kpi-value">${reportNumber(completion)}٪</span>`}</strong><div class="monthly-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${completion ?? 0} aria-label="درصد تکمیل داده">${completion !== null && html`<i style=${`width:${completion}%`}></i>`}</div><em>${statusLabel}</em></div><div class="monthly-kpi monthly-kpi--change"><span>تغییر نسبت به قبل</span><${MonthlyChange} report=${report}/></div></div>
    <div class="monthly-sheet__grid">
      <${Panel} key="monthly-identity" title="مشخصات دانش‌آموز" className="monthly-identity" tone="navy"><div class="report-portrait"><${StudentPhoto} report=${report}/></div><dl class="report-identity-list"><div><dt>نام و نام خانوادگی</dt><dd>${report.student.name}</dd></div><div><dt>کد ملی</dt><dd><bdi dir="ltr">${report.student.nationalId}</bdi></dd></div><div><dt>شماره دانش‌آموزی</dt><dd><bdi dir="ltr">${report.student.number}</bdi></dd></div><div><dt>پایه و کلاس</dt><dd>${report.academic.grade} · ${report.academic.className}</dd></div></dl></${Panel}>
      <${Panel} key="monthly-radar" title="نمودار ۹ حوزهٔ رشد" className="monthly-radar" tone="teal">${loading ? html`<${MissingSection} message="در حال آماده‌سازی گزارش…"/>` : radar ? html`<${EChart} option=${radar} label="نمودار راداری ۹ حوزهٔ رشد" className="echart--radar"/>` : html`<${MissingSection}/>`}</${Panel}>
      <${Panel} key="monthly-trend" title="روند ارزیابی ماهانه" className="monthly-trend" tone="navy">${loading ? html`<${MissingSection} message="در حال آماده‌سازی گزارش…"/>` : trend ? html`<${EChart} option=${trend} label="روند امتیازهای ارزیابی ماهانه" className="echart--trend echart--monthly-trend"/>` : html`<${MissingSection}/>`}</${Panel}>
      <${Panel} key="monthly-metrics" title="شاخص‌های آموزشی و رفتاری" className="monthly-metrics" tone="teal"><${MonthlyMetricTable} report=${report}/></${Panel}>
      <${Panel} key="monthly-strengths" title="نقاط قوت" className="monthly-strengths" tone="green">${strengths ? html`<${EChart} option=${strengths} label="نقاط قوت بر اساس شاخص‌ها" className="echart--bars"/>` : html`<${MissingSection}/>`}</${Panel}>
      <${Panel} key="monthly-improvements" title="نقاط قابل بهبود" className="monthly-improvements" tone="rose">${improvements ? html`<${EChart} option=${improvements} label="نقاط قابل بهبود بر اساس شاخص‌ها" className="echart--bars"/>` : html`<${MissingSection}/>`}</${Panel}>
      <${Panel} key="monthly-skills" title="مهارت‌های فردی" className="monthly-skills" tone="gold">${report.skills21?.length ? html`<div class="report-rating-list">${report.skills21.map(item => html`<div key=${item.code}><span>${item.title}</span><${Stars} value=${item.value}/><bdi class="monthly-skill-raw" dir="ltr">خام: ${rawMetricDisplay(item.rawValue)}</bdi><${MetricPercent} value=${item.value}/></div>`)}</div>` : html`<${MissingSection}/>`}</${Panel}>
      <${Panel} key="monthly-change-panel" title="تغییرات نسبت به ارزیابی قبلی" className="monthly-change-panel" tone="gold"><${MonthlyChange} report=${report}/>${report.monthlyChanges?.length ? html`<ul class="monthly-change-list">${report.monthlyChanges.slice(-3).map((item, index) => html`<li key=${`${item.from_month_no ?? 'missing'}-${item.to_month_no ?? 'missing'}-${index}`}><span>${item.from_month_no ?? '—'} ← ${item.to_month_no ?? '—'}</span><b>${isNumber(item.change) ? `${fa(item.change)} نمره` : 'ثبت نشده'}</b></li>`)}</ul>` : html`<${MissingSection} message="ارزیابی قبلی ثبت نشده است"/>`}</${Panel}>
      <${Panel} key="monthly-notes" title="توضیحات و پیشنهادها" className="monthly-notes" tone="navy">${report.recommendations?.length ? html`<ul class="report-bullet-list">${report.recommendations.map((item, index) => html`<li key=${`monthly-recommendation-${index}`}>${item}</li>`)}</ul>` : html`<${MissingSection}/>`}<p class="monthly-note-source">${sourceLabel}</p></${Panel}>
    </div>
    <${ReportFooter} report=${report} monthly/>
  </article>`;
}

function OfficialReport({ report, loading = false }) {
  const trend = trendOption(report.history); const radar = radarOption(report.domainScores?.length >= 3 ? report.domainScores : report.skills); const strengths = barsOption(report.strengths, '#0f766e'); const improvements = barsOption(report.improvements, '#a61d4d'); const readiness = barsOption(report.readiness, '#08766f');
  const attendanceRate = isNumber(report.attendance.rate) ? report.attendance.rate : null;
  return html`<article class="analytical-sheet analytical-sheet--official" data-report-mode="official_term" aria-label=${`کارنامه تحلیلی ${report.student.name}`}>
    <header class="analytical-sheet__header"><div class="analytical-sheet__mark"><${SchoolMark} report=${report}/></div><div class="analytical-sheet__heading"><p>${report.reportTitle}</p><h2>${report.academic.gradeRange}</h2><strong>${report.school}</strong></div><blockquote>« هیچ تلاشی بی‌نتیجه نیست؛<br/>هر قدم کوچک امروز، آینده‌ای بزرگ می‌سازد. »</blockquote></header>
    <div class="analytical-sheet__subhead"><span>${report.organization}</span><span>${report.academic.year} · ${report.academic.term} · کلاس ${report.academic.className}</span>${report.demo && html`<em>نمونهٔ نمایشی</em>`}</div>
    <${MetricAvailability} report=${report}/>
    <div class="analytical-sheet__grid">
      <${Panel} title="مشخصات دانش‌آموز" className="analytical-identity" tone="navy"><div class="report-portrait"><${StudentPhoto} report=${report}/></div><dl class="report-identity-list"><div><dt>نام و نام خانوادگی</dt><dd>${report.student.name}</dd></div><div><dt>کد ملی</dt><dd><bdi dir="ltr">${report.student.nationalId}</bdi></dd></div><div><dt>شماره دانش‌آموزی</dt><dd><bdi dir="ltr">${report.student.number}</bdi></dd></div><div><dt>پایه و کلاس</dt><dd>${report.academic.grade} · ${report.academic.className}</dd></div></dl><div class="report-mini-kpis"><span><small>معدل کل</small><strong>${isNumber(report.average) ? reportNumber(report.average) : '—'}</strong></span><span><small>رتبه کلاس</small><strong>${report.rank ? reportNumber(report.rank) : '—'}</strong></span></div></${Panel}>
      <${Panel} title="نمودار روند رشد سه‌ساله" className="analytical-trend" action="میانگین و رتبه"><div class="trend-caption">مقایسهٔ میانگین نهایی سه سال اخیر</div>${loading ? html`<${Empty}/>` : html`<${EChart} option=${trend} label="نمودار روند تحصیلی سه‌ساله" className="echart--trend"/>`}${report.history?.length ? html`<div class="report-trend-foot">${report.history.map(item => html`<span><b>${item.label}</b><i>${reportNumber(item.average)}</i>${item.rank ? html`<small>رتبه ${reportNumber(item.rank)}</small>` : null}</span>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="گزارش مشاور و پیگیری هوشمند" className="analytical-insights" tone="gold"><div class="report-insight-group"><h4>گزارش مشاور</h4>${report.counselor?.length ? html`<ul class="report-bullet-list">${report.counselor.map(item => html`<li>${item}</li>`)}</ul><${OverflowNote} count=${report.counselorOmitted}/>` : html`<${Empty}/>`}</div><div class="report-insight-group"><h4>موارد پیگیری</h4>${report.followUps?.length ? html`<ul class="report-bullet-list">${report.followUps.map(item => html`<li>${item}</li>`)}</ul><${OverflowNote} count=${report.followUpsOmitted}/>` : html`<${Empty}/>`}</div></${Panel}>
      <${Panel} title="وضعیت آموزشی و نمرات نهایی" className="analytical-table" tone="teal"><table class="report-score-table"><caption class="sr-only">نمرات و وضعیت آموزشی دانش‌آموز</caption><thead><tr><th scope="col">درس / شاخص</th><th scope="col">مستمر</th><th scope="col">میان‌ترم</th><th scope="col">پایانی</th><th scope="col">میانگین</th><th scope="col">وضعیت</th></tr></thead><tbody>${report.subjects.map(subject => html`<tr><th scope="row"><span class="report-score-table__subject">${subject.title}</span></th><td>${reportNumber(subject.continuous)}</td><td>${reportNumber(subject.midterm)}</td><td>${reportNumber(subject.final)}</td><td class=${isNumber(subject.current) && subject.current < 12 ? 'is-alert' : 'is-current'}>${reportNumber(subject.current)}</td><td><${SubjectStatus} subject=${subject}/></td></tr>`)}${report.subjectsOmitted ? html`<tr class="report-overflow-row"><td colspan="6"><${OverflowNote} count=${report.subjectsOmitted}/></td></tr>` : null}</tbody></table>${!report.subjects?.length && html`<${Empty}/>`}</${Panel}>
      <${Panel} title="نمودار ارزیابی مهارت‌ها" className="analytical-radar" tone="teal">${radar ? html`<${EChart} option=${radar} label="نمودار راداری مهارت‌های تحصیلی" className="echart--radar"/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="گزارش تربیتی و رفتاری" className="analytical-behavior" tone="gold">${report.skills?.length ? html`<div class="report-rating-list">${report.skills.map(item => html`<div><span>${item.title}</span><${Stars} value=${item.value}/><${MetricPercent} value=${item.value}/></div>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="نقاط قوت علمی" className="analytical-strengths" tone="green">${strengths ? html`<${EChart} option=${strengths} label="نقاط قوت علمی" className="echart--bars"/><${OverflowNote} count=${report.strengthsOmitted}/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="نقاط قابل بهبود" className="analytical-improvements" tone="rose">${improvements ? html`<${EChart} option=${improvements} label="نقاط قابل بهبود" className="echart--bars"/><${OverflowNote} count=${report.improvementsOmitted}/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="توصیه‌ها و برنامهٔ حمایت" className="analytical-recommendations" tone="gold"><div class="report-recommendation-grid"><${RecommendationGroup} title="والدین و دانش‌آموز" items=${report.recommendations} omitted=${report.recommendationsOmitted} ordered tone="gold"/><${RecommendationGroup} title="معلمان و کادر آموزشی" items=${report.teacherRecommendations} omitted=${report.teacherRecommendationsOmitted} tone="navy"/><${RecommendationGroup} title="حمایت خانواده" items=${report.support} omitted=${report.supportOmitted} tone="teal"/></div></${Panel}>
      <${Panel} title="حضور و غیاب" className="analytical-attendance" tone="navy"><div class="attendance-score"><strong>${attendanceRate === null ? '—' : html`${reportNumber(attendanceRate)}٪`}</strong><span>درصد حضور ثبت‌شده</span></div><div class="attendance-meta"><span>جلسات نهایی <b>${reportNumber(report.attendance.sessions)}</b></span><span>غیبت غیرموجه <b>${reportNumber(report.attendance.unexcused)}</b></span><span>تأخیر <b>${reportNumber(report.attendance.late)}</b></span></div></${Panel}>
      <${Panel} title="مهارت‌های قرن بیست‌ویکم" className="analytical-skills21" tone="teal">${report.skills21?.length ? html`<div class="report-rating-list">${report.skills21.map(item => html`<div><span>${item.title}</span><${Stars} value=${item.value}/><${MetricPercent} value=${item.value}/></div>`)}</div>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="مشارکت‌ها و فعالیت‌های مدرسه" className="analytical-activities" tone="teal">${report.activities?.length ? html`<div class="report-activities">${report.activities.map(item => html`<div><${Sticker} kind=${item.icon} title=${item.title}/><strong>${item.title}</strong><small>${item.text}</small></div>`)}</div><${OverflowNote} count=${report.activitiesOmitted}/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="آمادگی برای دوره متوسطه" className="analytical-readiness" tone="navy">${readiness ? html`<${EChart} option=${readiness} label="آمادگی تحصیلی برای دوره متوسطه" className="echart--readiness"/>` : html`<${Empty}/>`}</${Panel}>
      <${Panel} title="افتخارات و عناوین کسب‌شده" className="analytical-awards" tone="gold">${report.awards?.length ? html`<div class="report-awards">${report.awards.map(item => html`<div><${Sticker} kind=${item.icon} title=${item.title}/><span><b>${item.title}</b><small>${item.text}</small></span></div>`)}</div><${OverflowNote} count=${report.awardsOmitted}/>` : html`<${Empty}/>`}</${Panel}>
    </div>
    <${ReportFooter} report=${report}/>
  </article>`;
}

export function AnalyticalReport({ snapshot, loading = false }) {
  const report = useMemo(() => mapSnapshot(snapshot), [snapshot]);
  return report.reportMode === 'data_monthly'
    ? html`<${MonthlyReport} report=${report} loading=${loading}/>`
    : html`<${OfficialReport} report=${report} loading=${loading}/>`;
}
