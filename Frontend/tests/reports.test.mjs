import assert from 'node:assert/strict';
import test from 'node:test';

import { matchRoute } from '../src/core/router.js';
import {
  REPORT_CARD_TEMPLATES,
  buildReportDraftPayload,
  buildReportTemplatePayload,
  normalizeAcademicSettingsPayload,
  normalizeSummerThreshold,
} from '../src/core/report-cards.js';

const expectedTemplates = [
  'analytical_term_1',
  'analytical_term_2',
  'analytical_annual',
  'final_term_1',
  'final_term_2',
  'final_annual',
  'summer_report',
];

test('report workspace exposes exactly seven real period-specific printable layouts', () => {
  assert.deepEqual(REPORT_CARD_TEMPLATES.map(item => item.key), expectedTemplates);
  assert.equal(new Set(REPORT_CARD_TEMPLATES.map(item => item.key)).size, 7);
  assert.ok(REPORT_CARD_TEMPLATES.every(item => item.label && item.family && item.period));
  assert.ok(REPORT_CARD_TEMPLATES.filter(item => item.family === 'analytical').every(item => item.pageSize === 'A3 landscape'));
  assert.ok(REPORT_CARD_TEMPLATES.filter(item => item.family !== 'analytical').every(item => item.pageSize === 'A4 portrait'));
});

test('annual and summer draft requests do not fabricate an ordinary academic term', () => {
  assert.deepEqual(buildReportDraftPayload({
    templateId: 'template-annual', enrollmentId: 'enrollment-1', templateKey: 'final_annual',
  }), {
    template: 'template-annual', enrollment: 'enrollment-1',
  });

  assert.deepEqual(buildReportDraftPayload({
    templateId: 'template-summer', enrollmentId: 'enrollment-1', templateKey: 'summer_report',
    summerProgramId: 'summer-1', summerRegistrationId: 'registration-1',
  }), {
    template: 'template-summer', summer_registration: 'registration-1',
  });

  assert.deepEqual(buildReportDraftPayload({
    templateId: 'template-term', enrollmentId: 'enrollment-1', templateKey: 'final_term_1',
    termId: 'term-1',
  }), {
    template: 'template-term', enrollment: 'enrollment-1', term: 'term-1',
  });
});

test('new report templates use backend allowlisted blocks and canonical page-size keys', () => {
  for (const layout of REPORT_CARD_TEMPLATES) {
    const payload = buildReportTemplatePayload({
      organization: 'organization-1', school: 'school-1', templateKey: layout.key,
    });
    assert.equal(payload.layout_key, layout.key);
    assert.equal(payload.report_type, 'student_report_card');
    assert.ok(payload.blocks.length > 0);
    assert.ok(payload.blocks.includes('student_identity'));
    assert.equal(payload.presentation.page_size, layout.family === 'analytical' ? 'a3_landscape' : 'a4_portrait');
  }
});

test('academic settings preserve independent rank switches and reject invalid weights', () => {
  assert.deepEqual(normalizeAcademicSettingsPayload({
    school: 'school-1', academicYear: 'year-1', firstTermWeight: '1.5', secondTermWeight: '2',
    showClassRank: true, showGradeRank: false, showSchoolRank: true, reason: 'اصلاح سیاست آموزشی',
  }), {
    school: 'school-1', academic_year: 'year-1', first_term_weight: '1.5',
    second_term_weight: '2', show_class_rank: true, show_grade_rank: false,
    show_school_rank: true, reason: 'اصلاح سیاست آموزشی',
  });
  assert.throws(() => normalizeAcademicSettingsPayload({ firstTermWeight: '0', secondTermWeight: '2' }), /مثبت/);
  assert.throws(() => normalizeAcademicSettingsPayload({ firstTermWeight: '-1', secondTermWeight: '2' }), /مثبت/);
});

test('optional summer threshold remains null and enforces the inclusive educational range', () => {
  assert.equal(normalizeSummerThreshold(''), null);
  assert.equal(normalizeSummerThreshold(null), null);
  assert.equal(normalizeSummerThreshold('0'), '0');
  assert.equal(normalizeSummerThreshold('10.25'), '10.25');
  assert.equal(normalizeSummerThreshold('20'), '20');
  assert.throws(() => normalizeSummerThreshold('-1'), /۰ تا ۲۰/);
  assert.throws(() => normalizeSummerThreshold('20.01'), /۰ تا ۲۰/);
});

test('report and settings management routes declare role-based access', () => {
  const reportRoles = matchRoute('/reports').roles;
  const settingsRoles = matchRoute('/settings').roles;
  assert.ok(reportRoles.includes('school_manager'));
  assert.ok(reportRoles.includes('educational_deputy'));
  assert.ok(settingsRoles.includes('school_manager'));
  assert.ok(settingsRoles.includes('educational_deputy'));
  assert.ok(!settingsRoles.includes('teacher'));
  assert.ok(!settingsRoles.includes('operator'));
});

test('report API adapter sends real authenticated school-scoped management requests', async () => {
  const storage = () => ({ getItem: () => null, setItem() {}, removeItem() {} });
  globalThis.document = { querySelector: () => null };
  globalThis.window = { __HAMAMOOZ_CONFIG__: { apiBaseUrl: '/api/v1/' } };
  globalThis.location = { origin: 'https://school.example', search: '' };
  globalThis.localStorage = storage();
  globalThis.sessionStorage = storage();

  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ results: [], id: 'saved' }), {
      status: 200, headers: { 'content-type': 'application/json' },
    });
  };

  const { reportApi } = await import('../src/core/api.js');
  const { store } = await import('../src/core/store.js');
  store.patch({ accessToken: 'test-access-token', scope: { schoolId: 'school-42', organizationId: null } });

  await reportApi.settings({ academic_year: 'year-1' });
  await reportApi.updateSettings('settings-1', { first_term_weight: '1', second_term_weight: '2' });
  await reportApi.createDraft({ template: 'template-1', enrollment: 'enrollment-1', period_type: 'annual' });
  await reportApi.previewDraft('draft-1');
  await reportApi.transitionDraft('draft-1', 'approve');
  await reportApi.updateSummerScore('score-1', { value: '17.25' });
  await reportApi.finalizeSummerExam('exam-1');
  await reportApi.recalculateAnnual({ school: 'school-42', academic_year: 'year-1' });
  await reportApi.downloadArchive('archive-1', 'docx');

  assert.deepEqual(calls.map(call => new URL(call.url).pathname), [
    '/api/v1/academic-report-settings/',
    '/api/v1/academic-report-settings/settings-1/',
    '/api/v1/reports/drafts/',
    '/api/v1/reports/drafts/draft-1/preview/',
    '/api/v1/reports/drafts/draft-1/approve/',
    '/api/v1/summer-subject-scores/score-1/',
    '/api/v1/summer-exams/exam-1/finalize/',
    '/api/v1/annual-results/recalculate/',
    '/api/v1/reports/archive-1/download-docx/',
  ]);
  assert.deepEqual(calls.map(call => call.options.method), ['GET', 'PATCH', 'POST', 'GET', 'POST', 'PATCH', 'POST', 'POST', 'GET']);
  assert.ok(calls.every(call => call.options.headers.get('X-School-ID') === 'school-42'));
  assert.ok(calls.every(call => call.options.headers.get('Authorization') === 'Bearer test-access-token'));
});
