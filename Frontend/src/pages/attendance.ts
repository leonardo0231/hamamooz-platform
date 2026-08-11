import { navigate } from '../app/router.js';
import { renderAlertsPage } from './alerts.js';
import { renderResourcePage } from './resource.js';
import { h } from '../utils/dom.js';
import { icon } from '../components/icons.js';

type AttendanceTab = 'sessions' | 'records' | 'alerts' | 'notifications';

const tabs: Array<{ id: AttendanceTab; label: string; icon: string; href: string }> = [
  { id: 'sessions', label: 'حضور امروز و جلسات', icon: 'calendar', href: '/attendance' },
  { id: 'records', label: 'سوابق و عذرها', icon: 'check', href: '/attendance/records' },
  { id: 'alerts', label: 'هشدارهای غیبت', icon: 'bell', href: '/attendance/alerts' },
  { id: 'notifications', label: 'اعلان والدین', icon: 'file', href: '/attendance/notifications' },
];

function activeTab(routeTab?: string): AttendanceTab {
  if (routeTab === 'records' || routeTab === 'alerts' || routeTab === 'notifications') return routeTab;
  const view = new URLSearchParams(location.search).get('view');
  return view === 'records' || view === 'alerts' || view === 'notifications' ? view : 'sessions';
}

async function contentFor(tab: AttendanceTab): Promise<HTMLElement> {
  if (tab === 'alerts') return renderAlertsPage();
  if (tab === 'records') return renderResourcePage('attendance-records');
  if (tab === 'notifications') return renderResourcePage('parent-notifications');
  return renderResourcePage('attendance-sessions');
}

/**
 * Attendance keeps daily work in one local workspace. Policy configuration is
 * intentionally outside these tabs and belongs to Administration.
 */
export async function renderAttendancePage(routeTab?: string): Promise<HTMLElement> {
  const selected = activeTab(routeTab);
  const page = await contentFor(selected);
  const heading = page.querySelector('.page-heading');
  heading?.insertAdjacentElement('afterend', h(
    'nav',
    { className: 'section-tabs', 'aria-label': 'بخش‌های حضور و غیاب' },
    ...tabs.map(tab => h(
      'button',
      {
        className: `section-tab${tab.id === selected ? ' is-active' : ''}`,
        type: 'button',
        'aria-current': tab.id === selected ? 'page' : undefined,
        onClick: () => navigate(tab.href),
      },
      icon(tab.icon),
      tab.label,
    )),
  ));
  return page;
}
