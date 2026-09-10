import { html, useMemo } from '../core/view.js';
import { EChart } from './echart.js';
import { Icon } from './icons.js';

const normalizeNumericText = value => {
  if (typeof value !== 'string') return value;
  const digits = value
    .replace(/[۰-۹]/g, digit => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, digit => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/[٬،]/g, '')
    .replace(/٫/g, '.')
    .trim();
  return /^[-+]?\d+\/\d+$/.test(digits) ? digits.replace('/', '.') : digits;
};
const numericValue = value => {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  const numeric = Number(normalizeNumericText(value));
  return Number.isFinite(numeric) ? numeric : null;
};
const fa = value => {
  const numeric = numericValue(value);
  return numeric === null
    ? '—'
    : new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(numeric);
};
const clamp = (value, min = 0, max = 100) => {
  const numeric = numericValue(value);
  return numeric === null ? null : Math.max(min, Math.min(max, numeric));
};
const isNumber = value => numericValue(value) !== null;
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
const numericOrNull = value => numericValue(value);

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

const DOMAIN_WEIGHTS = Object.freeze({
  EDU: 20, DEV: 15, CHR: 15, DIS: 15, CUL: 7,
  RES: 8, SPT: 7, ART: 6, PER: 7,
});
const DOMAIN_METRIC_TOTALS = Object.freeze({
  EDU: 8, DEV: 5, CHR: 2, DIS: 5, CUL: 3,
  RES: 6, SPT: 7, ART: 7, PER: 3,
});
const MONTHLY_METRIC_TOTAL = 46;

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

// The summer report is easier to read when the 46 imported indicators are
// grouped by the same language used in the reference report.  Each group has
// its own compact chart and table; the raw value remains available in the
// table, but implementation codes never become part of the printed report.
const MONTHLY_METRIC_GROUPS = Object.freeze([
  { key: 'education', title: 'شاخص‌های آموزشی', eyebrow: 'یادگیری و عملکرد تحصیلی', codes: ['EDU'], chart: 'domains', tone: 'teal', color: '#0a746b' },
  { key: 'behavior', title: 'شاخص‌های رفتاری و تربیتی', eyebrow: 'پرورشی، تربیتی و انضباطی', codes: ['DEV', 'CHR', 'DIS'], chart: 'domains', tone: 'gold', color: '#b28a16' },
  { key: 'growth', title: 'شاخص‌های رشد تکمیلی', eyebrow: 'فرهنگی، پژوهشی، ورزشی و هنری', codes: ['CUL', 'RES', 'SPT', 'ART'], chart: 'domains', tone: 'purple', color: '#4a287d' },
  { key: 'personal', title: 'مهارت‌های فردی', eyebrow: 'ارتباط، برنامه‌ریزی و ارائه', codes: ['PER'], chart: 'domains', tone: 'navy', color: '#123d70' },
]);

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
  summerSubjectResults: [],
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
  summerSubjectResults: [],
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
  metricGroups: Object.fromEntries(MONTHLY_METRIC_GROUPS.map(group => [group.key, []])),
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

function normalizedUnit(value) {
  return normalizeNumericText(String(value ?? ''))
    .toLowerCase()
    .replace(/[‌\s]/g, '')
    .replace(/٪/g, '%');
}

function unitKind(value) {
  const unit = normalizedUnit(value);
  if (!unit) return null;
  if (['percent', 'percentage', '%', 'درصد', 'درصدی'].includes(unit)) return 'percent';
  if (['score_20', 'score20', '0-20', '0to20', '20', 'نمرهاز۲۰', 'نمره۲۰'].includes(unit)) return 'score20';
  if (['rubric_5', 'rubric5', 'score_5', 'score5', '0-5', '0to5', '5', 'نمرهاز۵', 'نمره۵'].includes(unit)) return 'rubric5';
  if (['ratio', 'نسبت', 'نسبتیتکمیل'].includes(unit)) return 'ratio';
  if (['delta', 'change', 'difference', 'تغییر', 'اختلاف'].includes(unit)) return 'delta';
  return null;
}

function metricUnit(item) {
  // `value_unit`/`unit`/`scale` are accepted for older snapshots; the newer
  // import adapter uses `raw_unit` so the source scale is never guessed from
  // the magnitude of a number.
  const declared = item.raw_unit ?? item.metric_unit ?? item.value_unit ?? item.unit ?? item.scale;
  if (declared !== undefined && declared !== null && declared !== '') return declared;
  const maxRawScore = numericValue(item.max_raw_score);
  return maxRawScore === 20 ? 'score_20' : maxRawScore === 5 ? 'rubric_5' : null;
}

function metricValue(value, unit = null) {
  const numeric = numericValue(value);
  if (numeric === null) return null;
  const kind = unitKind(unit);
  if (kind === 'percent') return numeric >= 0 && numeric <= 100 ? numeric : null;
  if (kind === 'score20') return numeric >= 0 && numeric <= 20 ? numeric * 5 : null;
  if (kind === 'delta') return null;
  // The API's default metric contract is an integer 0–5 rubric.  Without an
  // explicit unit, keep that strict boundary so a 0–20 grade or a signed
  // change cannot silently become a rubric score.
  if (kind && kind !== 'rubric5') return null;
  if (!Number.isInteger(numeric) || numeric < 0 || numeric > 5) return null;
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
  const rawUnit = metricUnit(source);
  const value = metricValue(rawValue, rawUnit);
  return {
    ...source,
    code,
    title: source.title ?? titleForMetric(code),
    rawValue,
    rawUnit,
    value,
    hasData: value !== null,
  };
}

function domainPercent(item) {
  if (!item || item.has_data === false || item.hasData === false) return null;
  if (isNumber(item.percent)) {
    const percent = numericValue(item.percent);
    return percent >= 0 && percent <= 100 ? percent : null;
  }
  const scoreUnit = unitKind(item.score_unit ?? item.unit ?? item.scale);
  if (isNumber(item.score)) {
    const score = numericValue(item.score);
    if (scoreUnit === 'percent') return score >= 0 && score <= 100 ? score : null;
    return score >= 0 && score <= 20 ? score * 5 : null;
  }
  // A bare `value` is ambiguous (it may be a 0–20 score or a percentage).
  // Only accept it when the producer declares its unit/scale explicitly;
  // otherwise keeping the domain missing is safer than silently converting it.
  if (isNumber(item.value)) {
    const value = numericValue(item.value);
    const unit = unitKind(item.value_unit ?? item.unit ?? item.scale);
    if (unit === 'percent') {
      return value >= 0 && value <= 100 ? value : null;
    }
    if (unit === 'score20') {
      return value >= 0 && value <= 20 ? value * 5 : null;
    }
  }
  return null;
}

function normalizeCompletionPercent(report, metricRows) {
  const explicitValue = hasOwn(report, 'completion_percent')
    ? report.completion_percent
    : hasOwn(report, 'completion_ratio')
      ? report.completion_ratio
      : report.completion;
  if (isNumber(explicitValue)) {
    const explicitUnit = unitKind(report.completion_percent_unit ?? report.completion_unit ?? report.completion_scale);
    const value = numericValue(explicitValue);
    if (explicitUnit === 'ratio' || hasOwn(report, 'completion_ratio')) return clamp(value * 100);
    return clamp(value);
  }
  const completed = numericOrNull(report?.completed_metrics)
    ?? metricRows.filter(item => item.hasData).length;
  const total = numericOrNull(report?.total_metrics)
    ?? numericOrNull(report?.required_metrics)
    ?? MONTHLY_METRIC_TOTAL;
  return total > 0 ? clamp((completed / total) * 100) : null;
}

function weightedOverallScore(domainScores) {
  const scored = (Array.isArray(domainScores) ? domainScores : [])
    .map(item => ({ value: numericValue(item?.value), weight: numericValue(item?.weight) ?? DOMAIN_WEIGHTS[item?.code] }))
    .filter(item => item.value !== null && item.weight > 0);
  const totalWeight = scored.reduce((sum, item) => sum + item.weight, 0);
  if (!totalWeight) return null;
  const score = scored.reduce((sum, item) => sum + (item.value / 5) * item.weight, 0) / totalWeight;
  return Math.round(score * 100) / 100;
}

function monthlyChangeFromHistory(history, currentMonthNo = null) {
  if (!Array.isArray(history) || history.length < 2) return null;
  const latest = currentMonthNo === null
    ? history.at(-1)
    : history.find(item => item.monthNo === currentMonthNo) ?? history.at(-1);
  const latestIndex = history.indexOf(latest);
  const previous = latestIndex > 0 ? history[latestIndex - 1] : history.at(-2);
  if (!latest || !previous) return null;
  return Math.round((latest.average - previous.average) * 100) / 100;
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
  const rowByCode = new Map(sourceRows.map(item => {
    const rawCode = String(item?.code ?? item?.domain_code ?? '').toUpperCase();
    return [rawCode.split('_', 1)[0], item];
  }));
  const metricGroups = new Map();
  for (const item of metricRows) {
    const code = metricDomainCode(item);
    if (!code) continue;
    // mapSnapshot has already converted valid scaled scores to percentages;
    // applying metricValue a second time would discard every value above 5.
    const value = item.hasData === false || !isNumber(item.value)
      ? null
      : Number(item.value) >= 0 && Number(item.value) <= 100 ? Number(item.value) : null;
    if (value !== null) metricGroups.set(code, [...(metricGroups.get(code) ?? []), value]);
  }
  return ANALYSIS_DOMAINS.map(domain => {
    const source = rowByCode.get(domain.code);
    const values = metricGroups.get(domain.code) ?? [];
    const sourceValue = source ? domainPercent(source) : null;
    // Raw metric rows are the recovery path when an imported workbook has a
    // stale formula, an unlabelled percent, or a null summary column.  A
    // domain summary must not erase valid indicators just because its cached
    // spreadsheet formula is malformed.
    const value = sourceValue !== null
      ? sourceValue
      : values.length ? clamp(values.reduce((sum, item) => sum + item, 0) / values.length) : null;
    const completedMetrics = values.length > 0
      ? values.length
      : source?.completed_metrics ?? source?.completedMetrics
        ?? (value === null ? 0 : 1);
    const totalMetrics = source?.total_metrics ?? source?.totalMetrics
      ?? DOMAIN_METRIC_TOTALS[domain.code] ?? values.length;
    return {
      ...domain,
      ...source,
      code: domain.code,
      title: source?.title ?? source?.domain_title ?? domain.title,
      weight: source?.weight ?? DOMAIN_WEIGHTS[domain.code],
      value,
      percent: value,
      completedMetrics,
      totalMetrics,
      hasData: value !== null,
    };
  });
}

function buildMonthlyMetricGroups(metricRows) {
  return Object.fromEntries(MONTHLY_METRIC_GROUPS.map(group => [
    group.key,
    metricRows.filter(item => group.codes.includes(metricDomainCode(item))),
  ]));
}

function normalizeMonthlySubjectRows(rows) {
  const sourceRows = Array.isArray(rows) ? rows : [];
  return sourceRows.map(item => {
    const source = item && typeof item === 'object' ? item : { title: item };
    const title = String(source.title ?? source.subject ?? source.name ?? 'درس ثبت نشده').trim();
    const rawScore = source.final_score ?? source.finalScore ?? source.final
      ?? source.score ?? source.grade ?? source.current ?? source.value;
    return {
      ...source,
      title,
      score: numericSubject(rawScore),
      percent: numericValue(source.percent ?? source.percentage),
    };
  }).filter(item => item.title);
}

function normalizeSummerSubjectRows(rows) {
  const sourceRows = Array.isArray(rows) ? rows : [];
  return sourceRows.map((item, index) => {
    const source = item && typeof item === 'object' ? item : { subject_title: item };
    const title = String(source.subject_title ?? source.subject ?? source.title ?? 'درس ثبت نشده').trim() || 'درس ثبت نشده';
    const rawScore = source.score ?? source.final_score ?? source.finalScore ?? source.final ?? source.grade;
    const rawFinalScore = source.final_score ?? source.finalScore ?? source.final ?? source.score ?? source.grade;
    return {
      ...source,
      key: source.id ?? `${title}-${source.source_row ?? source.sourceRow ?? index}`,
      title,
      score: numericSubject(rawScore),
      finalScore: numericSubject(rawFinalScore),
      percent: numericValue(source.percent ?? source.percentage),
      rank: numericValue(source.rank),
      overallRank: numericValue(source.overall_rank ?? source.overallRank),
    };
  });
}

function mapDataMonthlyReport(report) {
  // ``monthly-preview`` is deliberately a separate API contract.  Optional
  // subject_grades are accepted only when the source explicitly provides them;
  // the renderer never derives official grades from indicator values.
  const rawMetrics = Array.isArray(report?.metrics) ? report.metrics : [];
  // Keep every coded metric row, including an invalid/raw value such as
  // «ندارد».  The table uses rawValue for auditability while value is the
  // explicitly scaled score converted to a percentage.
  const metricRows = rawMetrics.map(normalizeMetricRow).filter(item => item.code);
  const metricGroups = buildMonthlyMetricGroups(metricRows);
  const subjectRows = normalizeMonthlySubjectRows(
    Array.isArray(report?.subject_grades) ? report.subject_grades : report?.subjects,
  );
  const visibleSubjects = bounded(subjectRows, 12);
  // ``summer_subject_results`` is an independent exam collection.  Do not
  // fold it into ``subjects``: that field is reserved for explicit official
  // subject grades supplied by the report producer.
  const visibleSummerSubjectResults = bounded(
    normalizeSummerSubjectRows(report?.summer_subject_results),
    12,
  );
  const behavior = metricRows.filter(item => /^(DEV|CHR|DIS)_/.test(item.code ?? ''));
  const skills21 = metricRows.filter(item => /^PER_/.test(item.code ?? ''));
  const indexRows = metricRows.filter(item => /^(EDU|DEV|CHR|DIS)_/.test(item.code ?? ''));
  const domainScores = normalizeDomainScores(report?.domains, metricRows);
  const metricInsights = metricRows
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
  const overallScore = numericSubject(report?.overall_score) ?? weightedOverallScore(domainScores);
  const completionPercent = normalizeCompletionPercent(report, metricRows);
  const sourceMonthlyChanges = Array.isArray(report?.monthly_changes) ? report.monthly_changes : [];
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
    .filter(Boolean)
    .sort((left, right) => {
      if (left.monthNo === null && right.monthNo === null) return 0;
      if (left.monthNo === null) return 1;
      if (right.monthNo === null) return -1;
      return left.monthNo - right.monthNo;
    });
  if (overallScore !== null && !history.some(item => item.monthNo !== null && item.monthNo === currentMonthNo)) {
    history.push({ label: month.title ?? 'ماه جاری', average: overallScore, rank: null, monthNo: currentMonthNo });
  }
  const derivedMonthlyChanges = history.length > 1
    ? history.slice(1).map((item, index) => {
      const previous = history[index];
      return {
        from_month_no: previous.monthNo,
        to_month_no: item.monthNo,
        from_month_title: previous.label,
        to_month_title: item.label,
        change: Math.round((item.average - previous.average) * 100) / 100,
      };
    })
    : [];
  const monthlyChanges = sourceMonthlyChanges.length ? sourceMonthlyChanges : derivedMonthlyChanges;
  const declaredChange = numericOrNull(report?.monthly_change);
  const currentChange = declaredChange
    ?? (currentMonthNo === null ? null : numericOrNull(monthlyChanges.find(item => numericOrNull(item?.to_month_no) === currentMonthNo)?.change))
    ?? monthlyChangeFromHistory(history, currentMonthNo);
  const organizationSource = typeof report?.organization === 'object' ? report.organization : {};
  const schoolSource = typeof report?.school === 'object' ? report.school : {};
  const fallbackOrganization = typeof report?.organization === 'string' ? report.organization : 'ثبت نشده';
  const fallbackSchool = typeof report?.school === 'string' ? report.school : 'ثبت نشده';
  const summerTitle = 'کارنامه ارزیابی تابستانه رشد دانش‌آموز';
  const requestedTitle = typeof report?.title === 'string' ? report.title.trim() : '';
  const reportTitle = requestedTitle && !/سه\s*ساله/.test(requestedTitle) ? requestedTitle : summerTitle;
  const sourceSections = (Array.isArray(report?.missing_sections) ? report.missing_sections : [])
    .filter(section => !(section === 'official_subject_grades' && visibleSubjects.items.length));
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
    subjects: visibleSubjects.items,
    summerSubjectResults: visibleSummerSubjectResults.items,
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
    completionPercent,
    completionStatus: report?.completion_status ?? (completionPercent >= 100 ? 'final' : 'provisional'),
    monthlyChange: currentChange,
    monthlyChanges,
    monthlyScores: history,
    monthlyHistory: history,
    metricGroups,
    metricRows,
    indexRows,
    sourceFile: report?.source_file ?? '',
    sourceRow: report?.source_row ?? null,
    missingSections: sourceSections,
    subjectsOmitted: visibleSubjects.omitted,
    summerSubjectResultsOmitted: visibleSummerSubjectResults.omitted,
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
  const visibleSummerSubjectResults = bounded(
    normalizeSummerSubjectRows(report.summer_subject_results),
    12,
  );
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
    subjects: visibleSubjects.items,
    summerSubjectResults: visibleSummerSubjectResults.items,
    skills: behavior, skills21, readiness: academic, domainScores,
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
    subjectsOmitted: visibleSubjects.omitted,
    summerSubjectResultsOmitted: visibleSummerSubjectResults.omitted,
    strengthsOmitted: Math.max(0, strengthRows.length - strengths.items.length),
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
// Kept for compatibility with older report templates.  Current score tables
// intentionally omit the status column and do not call this helper.
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
  const heading = monthly ? 'امضا و تأیید مدرسه' : 'امضا و تأیید مسئولان مدرسه';
  const note = monthly ? '' : 'این کارنامه تصویری جامع از مسیر رشد علمی، تربیتی و شخصیتی دانش‌آموز است.';
  return html`<footer class=${`analytical-sheet__footer ${monthly ? 'monthly-sheet__footer' : ''}`}>
    <div class="report-footer-signatures"><div class="report-signature-heading"><strong>${heading}</strong>${note && html`<span>${note}</span>`}</div><div class="report-signatures">${report.signatures.map((label, index) => html`<span key=${`signature-${monthly ? 'monthly-' : ''}${index}`}>${label}</span>`)}</div></div>
    <div class=${`report-footer-note ${monthly ? 'report-footer-note--monthly' : ''}`}><span>هم‌آموز</span><strong>${monthly ? 'گزارش رشد ماهانه' : 'گزارش جامع رشد دانش‌آموز'}</strong>${!monthly && html`<p>رشد هر دانش‌آموز، مسیر منحصربه‌فردی است که با همراهی مدرسه و خانواده کامل می‌شود.</p>`}</div>
    <div class="report-footer-brand"><div class="report-footer-brand__mark"><${SchoolMark} report=${report}/></div><strong>${report.school}</strong><span>${report.organization}</span><small>برای رشد، یادگیری و ساختن آینده‌ای روشن</small></div>
  </footer>`;
}

function MonthlyMetricTable({ rows, caption, showDomain = false }) {
  const sourceRows = Array.isArray(rows) ? rows : [];
  if (!sourceRows.length) return html`<${MissingSection}/>`;
  // Two small tables keep long groups such as cultural/research/arts readable
  // on the A3 sheet without reducing the raw-data audit trail to a scroll area.
  const chunks = sourceRows.length > 4
    ? [sourceRows.slice(0, Math.ceil(sourceRows.length / 2)), sourceRows.slice(Math.ceil(sourceRows.length / 2))]
    : [sourceRows];
  const renderTable = (chunk, tableIndex) => html`<table key=${`${caption}-${tableIndex}`} class="report-score-table report-monthly-metric-table"><caption class="sr-only">${caption}</caption><thead><tr><th scope="col">شاخص</th>${showDomain ? html`<th scope="col">حوزه</th>` : null}<th scope="col">مقدار خام</th><th scope="col">امتیاز</th></tr></thead><tbody>${chunk.map(item => {
    const available = item.hasData && isNumber(item.value);
    const domain = ANALYSIS_DOMAINS.find(candidate => candidate.code === metricDomainCode(item));
    return html`<tr key=${item.code} class=${available ? 'is-available' : 'is-missing'}><th scope="row"><span class="report-score-table__subject">${item.title}</span></th>${showDomain ? html`<td>${item.domain_title ?? domain?.title ?? 'ثبت نشده'}</td>` : null}<td><bdi class="report-raw-value" dir="ltr">${rawMetricDisplay(item.rawValue)}</bdi></td><td>${available ? html`<${MetricPercent} value=${item.value}/>` : html`<span class="report-rating-missing">ثبت نشده</span>`}</td></tr>`;
  })}</tbody></table>`;
  return html`<div class="report-monthly-metric-tables">${chunks.map(renderTable)}</div>`;
}

function MonthlySubjectGradesTable({ rows }) {
  const sourceRows = Array.isArray(rows) ? rows : [];
  if (!sourceRows.length) return null;
  const splitAt = Math.ceil(sourceRows.length / 2);
  const chunks = [sourceRows.slice(0, splitAt), sourceRows.slice(splitAt)].filter(chunk => chunk.length);
  const renderTable = (chunk, tableIndex) => html`<table key=${`monthly-subject-grades-${tableIndex}`} class="report-score-table monthly-subject-grades__table"><caption class="sr-only">نمرات درسی دانش‌آموز</caption><thead><tr><th scope="col">درس</th><th scope="col">نمره از ۲۰</th></tr></thead><tbody>${chunk.map(subject => {
    const scoreClass = isNumber(subject.score) && subject.score < 12 ? 'is-alert' : 'is-current';
    return html`<tr key=${subject.title}><th scope="row"><span class="report-score-table__subject">${subject.title}</span></th><td class=${isNumber(subject.score) ? scoreClass : 'report-rating-missing'}>${isNumber(subject.score) ? reportNumber(subject.score) : 'ثبت نشده'}</td></tr>`;
  })}</tbody></table>`;
  return html`<section class="monthly-subject-grades" aria-labelledby="monthly-subject-grades-title"><div class="monthly-subject-grades__heading"><h4 id="monthly-subject-grades-title">نمرات درسی دانش‌آموز</h4><span>مقیاس ۰ تا ۲۰</span></div><div class="monthly-subject-grades__tables">${chunks.map(renderTable)}</div></section>`;
}

function MonthlyMetricSection({ report, group }) {
  const rows = report.metricGroups?.[group.key] ?? [];
  if (!rows.length) {
    return html`<${Panel} title=${group.title} className=${`monthly-metric-section monthly-metric-section--${group.key}`} tone=${group.tone}><${MissingSection}/></${Panel}>`;
  }
  const domains = group.codes
    .map(code => report.domainScores?.find(item => item.code === code))
    .filter(item => item?.hasData && isNumber(item.value))
    .map(item => ({ title: item.title, value: item.value }));
  const chartItems = group.chart === 'metrics'
    ? rows.filter(item => item.hasData && isNumber(item.value)).map(item => ({ title: item.title, value: item.value }))
    : domains;
  const chart = barsOption(chartItems, group.color);
  return html`<${Panel} title=${group.title} className=${`monthly-metric-section monthly-metric-section--${group.key}`} tone=${group.tone}>
    <div class="monthly-metric-section__intro"><span>${group.eyebrow}</span><b>امتیازها از شاخص‌های ثبت‌شده</b></div>
    ${chart ? html`<${EChart} option=${chart} label=${`${group.title} به تفکیک ${group.chart === 'metrics' ? 'شاخص' : 'حوزه'}`} className="echart--metric-group"/>` : null}
    <${MonthlyMetricTable} rows=${rows} caption=${group.title} showDomain=${group.codes.length > 1}/>
    ${group.key === 'personal' ? html`<${MonthlySubjectGradesTable} rows=${report.subjects}/>` : null}
  </${Panel}>`;
}

function MonthlyReport({ report, loading = false }) {
  const trend = trendOption(report.monthlyHistory ?? report.history);
  const radar = radarOption(report.domainScores);
  const strengths = barsOption(report.strengths, '#0f766e');
  const improvements = barsOption(report.improvements, '#a61d4d');
  const average = isNumber(report.average) ? report.average : null;
  const hasTrend = (report.monthlyHistory ?? report.history)?.length > 1;
  return html`<article class="analytical-sheet analytical-sheet--monthly" data-report-mode="data_monthly" aria-label=${`کارنامه تابستانه ${report.student.name}`}>
    <header class="analytical-sheet__header monthly-sheet__header"><div class="analytical-sheet__mark"><${SchoolMark} report=${report}/></div><div class="analytical-sheet__heading"><p>${report.reportTitle}</p><h2>${report.academic.term}</h2><strong>${report.school}</strong></div><div class="monthly-sheet__meta"><strong>گزارش شاخص‌محور</strong><span>${report.organization}</span><span>${report.academic.grade} · کلاس ${report.academic.className}</span></div></header>
    <div class="analytical-sheet__subhead monthly-sheet__subhead"><span>ارزیابی تابستانه بر اساس شاخص‌های رشد</span><span>${report.academic.term}</span></div>
    <div class="monthly-kpi-strip" aria-label="خلاصهٔ امتیاز گزارش"><div class="monthly-kpi monthly-kpi--overall"><span>امتیاز کلی شاخص‌ها</span><strong>${average === null ? 'ثبت نشده' : html`<span class="monthly-kpi-value">${reportNumber(average)} <small>از ۲۰</small></span>`}</strong><em>میانگین نمره‌های ثبت‌شده</em></div></div>
    <div class="monthly-sheet__grid">
      <${Panel} key="monthly-identity" title="مشخصات دانش‌آموز" className="monthly-identity" tone="navy"><div class="report-portrait"><${StudentPhoto} report=${report}/></div><dl class="report-identity-list"><div><dt>نام و نام خانوادگی</dt><dd>${report.student.name}</dd></div><div><dt>کد ملی</dt><dd><bdi dir="ltr">${report.student.nationalId}</bdi></dd></div><div><dt>شماره دانش‌آموزی</dt><dd><bdi dir="ltr">${report.student.number}</bdi></dd></div><div><dt>پایه و کلاس</dt><dd>${report.academic.grade} · ${report.academic.className}</dd></div></dl></${Panel}>
      <${Panel} key="monthly-radar" title="نمودار ۹ حوزهٔ رشد" className="monthly-radar" tone="teal">${loading ? html`<${MissingSection} message="در حال آماده‌سازی گزارش…"/>` : radar ? html`<${EChart} option=${radar} label="نمودار راداری ۹ حوزهٔ رشد" className="echart--radar"/>` : html`<${MissingSection}/>`}</${Panel}>
      ${hasTrend && html`<${Panel} key="monthly-trend" title="روند امتیازهای ماهانه" className="monthly-trend" tone="navy">${loading ? html`<${MissingSection} message="در حال آماده‌سازی گزارش…"/>` : trend ? html`<${EChart} option=${trend} label="روند امتیازهای ارزیابی ماهانه" className="echart--trend echart--monthly-trend"/>` : html`<${MissingSection}/>`}</${Panel}>`}
      ${MONTHLY_METRIC_GROUPS.map(group => html`<${MonthlyMetricSection} key=${`monthly-group-${group.key}`} report=${report} group=${group}/>`)}
      <${Panel} key="monthly-strengths" title="نقاط قوت" className="monthly-strengths" tone="green">${strengths ? html`<${EChart} option=${strengths} label="نقاط قوت بر اساس شاخص‌ها" className="echart--bars"/>` : html`<${MissingSection}/>`}</${Panel}>
      <${Panel} key="monthly-improvements" title="نقاط قابل بهبود" className="monthly-improvements" tone="rose">${improvements ? html`<${EChart} option=${improvements} label="نقاط قابل بهبود بر اساس شاخص‌ها" className="echart--bars"/>` : html`<${MissingSection}/>`}</${Panel}>
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
      <${Panel} title="وضعیت آموزشی و نمرات نهایی" className="analytical-table" tone="teal"><table class="report-score-table"><caption class="sr-only">نمرات و وضعیت آموزشی دانش‌آموز</caption><thead><tr><th scope="col">درس / شاخص</th><th scope="col">مستمر</th><th scope="col">میان‌ترم</th><th scope="col">پایانی</th><th scope="col">میانگین</th></tr></thead><tbody>${report.subjects.map(subject => html`<tr><th scope="row"><span class="report-score-table__subject">${subject.title}</span></th><td>${reportNumber(subject.continuous)}</td><td>${reportNumber(subject.midterm)}</td><td>${reportNumber(subject.final)}</td><td class=${isNumber(subject.current) && subject.current < 12 ? 'is-alert' : 'is-current'}>${reportNumber(subject.current)}</td></tr>`)}${report.subjectsOmitted ? html`<tr class="report-overflow-row"><td colspan="5"><${OverflowNote} count=${report.subjectsOmitted}/></td></tr>` : null}</tbody></table>${!report.subjects?.length && html`<${Empty}/>`}</${Panel}>
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
