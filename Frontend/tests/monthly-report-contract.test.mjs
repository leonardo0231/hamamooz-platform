import test from 'node:test';
import assert from 'node:assert/strict';

import { mapSnapshot } from '../src/components/analytical-report.js';

test('the data-monthly API contract renders without inventing official data', () => {
  const report = mapSnapshot({
    report_mode: 'data_monthly',
    title: 'کارنامه جامع رشد سه ساله دانش‌آموز',
    month: { no: 3, title: 'شهریور' },
    student: {
      name: 'آرین محمدی', national_id: '0012345678', student_number: null,
      class_code: '902', grade: 'هشتم', photo_url: '',
    },
    metrics: [
      { code: 'EDU_01', title: 'نمرات درسی', raw_score: 5, score: 20 },
      { code: 'EDU_02', title: 'پیشرفت نسبت به قبل', raw_score: 'ندارد', score: null },
      { code: 'DEV_01', title: 'احترام و همکاری', raw_score: 3, score: 12 },
      { code: 'PER_01', title: 'مدیریت زمان', raw_score: null, score: null },
    ],
    domains: [
      { code: 'EDU', title: 'آموزشی', score: 20, completed_metrics: 1 },
      { code: 'DEV', title: 'پرورشی', score: 12, completed_metrics: 1 },
    ],
    overall_score: 16.57,
    completion_percent: 40,
    completion_status: 'provisional',
    monthly_changes: [{ from_month_no: 1, to_month_no: 3, change: 1.57 }],
    monthly_scores: [
      { month_no: 1, overall_score: 15 },
      { month_no: 2, overall_score: null },
      { month_no: 3, overall_score: 16.57 },
    ],
    strengths: [{ code: 'EDU', title: 'آموزشی', score: 20 }],
    improvements: [{ code: 'DEV', title: 'پرورشی', score: 12 }],
    attendance: null,
    activities: [], awards: [], recommendations: [],
    missing_sections: ['attendance', 'official_subject_grades'],
  });

  assert.equal(report.demo, false);
  assert.equal(report.reportMode, 'data_monthly');
  assert.equal(report.reportTitle, 'کارنامه ارزیابی تابستانه رشد دانش‌آموز');
  assert.equal(report.academic.term, 'شهریور · گزارش ماهانه');
  assert.equal(report.student.number, '—');
  assert.equal(report.subjects.length, 0);
  assert.equal(report.average, 16.57);
  assert.equal(report.completionPercent, 40);
  assert.equal(report.monthlyChange, 1.57);
  assert.deepEqual(report.monthlyHistory.map(item => item.label), ['تیر', 'شهریور']);
  assert.equal(report.domainScores.length, 9);
  assert.equal(report.domainScores.find(item => item.code === 'EDU').value, 100);
  assert.equal(report.strengths[0].value, 100);
  assert.equal(report.improvements[0].value, 60);
  assert.equal(report.metricRows.find(item => item.code === 'EDU_02').rawValue, 'ندارد');
  assert.equal(report.metricRows.find(item => item.code === 'EDU_02').hasData, false);
  assert.equal(report.metricRows.find(item => item.code === 'EDU_02').value, null);
  assert.equal(report.indexRows.length, 3);
  assert.equal(report.skills21[0].hasData, false);
  assert.equal(report.readiness.length, 0);
  assert.equal(report.activities.length, 0);
  assert.equal(report.awards.length, 0);
  assert.deepEqual(report.missingSections, ['attendance', 'official_subject_grades']);
  assert.equal(report.attendance.rate, null);
});

test('Excel mixed scales are normalized from raw metrics and recover broken summaries', () => {
  const rawValues = [
    ['EDU_01', 18.64, 'score_20'], ['EDU_02', 'ندارد', 'delta'],
    ['EDU_03', 4], ['EDU_04', 4], ['EDU_05', 4], ['EDU_06', 3], ['EDU_07', 4], ['EDU_08', 3],
    ['DEV_01', 4], ['DEV_02', 2], ['DEV_03', 3], ['DEV_04', 5], ['DEV_05', 4],
    ['CHR_01', 4], ['CHR_02', 4],
    ['DIS_01', 4], ['DIS_02', 3], ['DIS_03', 4], ['DIS_04', 4], ['DIS_05', 3],
    ['CUL_01', 4], ['CUL_02', 4], ['CUL_03', 4],
    ['RES_01', 4], ['RES_02', 4], ['RES_03', 4], ['RES_04', 4], ['RES_05', 4], ['RES_06', 4],
    ['SPT_01', 4], ['SPT_02', 5], ['SPT_03', 4], ['SPT_04', 4], ['SPT_05', 4], ['SPT_06', 0], ['SPT_07', 5],
    ['ART_01', 3], ['ART_02', 3], ['ART_03', 3], ['ART_04', 4], ['ART_05', 4], ['ART_06', 0], ['ART_07', 4],
    ['PER_01', 3], ['PER_02', 3], ['PER_03', 4],
  ];
  const report = mapSnapshot({
    report_mode: 'data_monthly',
    title: 'کارنامه جامع رشد سه ساله دانش‌آموز',
    month: { no: 3, title: 'شهریور' },
    student: { name: 'نمونه', grade: 'هشتم', class_code: '803' },
    metrics: rawValues.map(([code, raw_score, raw_unit]) => ({ code, raw_score, raw_unit })),
    domains: [],
    overall_score: '#VALUE!',
    completed_metrics: 45,
    required_metrics: 46,
    completion_ratio: 45 / 46,
    monthly_scores: [{ month_no: 3, overall_score: '#VALUE!' }],
  });

  assert.equal(report.metricRows.length, 46);
  assert.equal(report.metricRows.find(item => item.code === 'EDU_01').value, 93.2);
  assert.equal(report.metricRows.find(item => item.code === 'EDU_02').rawValue, 'ندارد');
  assert.equal(report.metricRows.find(item => item.code === 'EDU_02').value, null);
  assert.equal(report.domainScores.length, 9);
  assert.equal(report.domainScores.every(item => item.hasData), true);
  assert.equal(Math.round(report.domainScores.find(item => item.code === 'EDU').value * 100) / 100, 76.17);
  assert.equal(Math.round(report.domainScores.find(item => item.code === 'ART').value * 100) / 100, 60);
  assert.equal(report.average, 14.86);
  assert.equal(Math.round(report.completionPercent * 100) / 100, 97.83);
  assert.deepEqual(report.monthlyHistory.map(item => item.label), ['شهریور']);
  assert.equal(report.monthlyHistory[0].average, 14.86);
  assert.equal(report.monthlyChange, null);
});
