import { renderResourcePage } from './resource.js';
import { navigate } from '../app/router.js';
import { h } from '../utils/dom.js';
import { icon } from '../components/icons.js';

export async function renderAttendancePage(): Promise<HTMLElement> {
  const resource = await renderResourcePage('attendance-sessions');
  const heading = resource.querySelector('.page-heading');
  heading?.insertAdjacentElement('afterend', h('nav', { className: 'section-tabs', 'aria-label': 'بخش‌های حضور و غیاب' },
    h('button', { className: 'section-tab is-active', type: 'button', 'aria-current': 'page' }, icon('calendar'), 'جلسات'),
    h('button', { className: 'section-tab', type: 'button', onClick: () => navigate('/resources/attendance-records') }, icon('check'), 'رکوردها و عذرها'),
    h('button', { className: 'section-tab', type: 'button', onClick: () => navigate('/resources/attendance-policies') }, icon('settings'), 'سیاست‌ها'),
    h('button', { className: 'section-tab', type: 'button', onClick: () => navigate('/alerts') }, icon('bell'), 'هشدارها'),
    h('button', { className: 'section-tab', type: 'button', onClick: () => navigate('/resources/parent-notifications') }, icon('file'), 'اعلان والدین'),
  ));
  return resource;
}
