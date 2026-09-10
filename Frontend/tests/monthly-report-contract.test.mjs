import test from 'node:test';
import assert from 'node:assert/strict';

import { mapSnapshot } from '../src/components/analytical-report.js';

test('the data-monthly API contract renders without inventing official data', () => {
  const report = mapSnapshot({
    report_mode: 'data_monthly',
    title: 'کارنامه ارزیابی تابستانه رشد دانش‌آموز',
    month: { no: 3, title: 'شهریور' },
    student: {
      name: 'آرین محمدی', national_id: '0012345678', student_number: null,
      class_code: '902', grade: 'هشتم', photo_url: '',
    },
    metrics: [
      { code: 'EDU_01', title: 'نمرات درسی', raw_score: 5, score: 20 },
      { code: 'DEV_01', title: 'احترام و همکاری', raw_score: 3, score: 12 },
      { code: 'PER_01', title: 'مدیریت زمان', raw_score: null, score: null },
    ],
    domains: [
      { code: 'EDU', title: 'آموزشی', score: 20, completed_metrics: 1 },
      { code: 'DEV', title: 'پرورشی', score: 12, completed_metrics: 1 },
    ],
    overall_score: 16.57,
    strengths: [{ code: 'EDU', title: 'آموزشی', score: 20 }],
    improvements: [{ code: 'DEV', title: 'پرورشی', score: 12 }],
    attendance: null,
    activities: [], awards: [], recommendations: [],
    missing_sections: ['attendance', 'official_subject_grades'],
  });

  assert.equal(report.demo, false);
  assert.equal(report.reportTitle, 'کارنامه ارزیابی تابستانه رشد دانش‌آموز');
  assert.equal(report.academic.term, 'شهریور · گزارش ماهانه');
  assert.equal(report.student.number, '—');
  assert.equal(report.subjects.length, 0);
  assert.equal(report.average, 16.57);
  assert.equal(report.domainScores.find(item => item.code === 'EDU').value, 100);
  assert.equal(report.strengths[0].value, 100);
  assert.equal(report.improvements[0].value, 60);
  assert.equal(report.skills21[0].hasData, false);
  assert.equal(report.attendance.rate, null);
});
