import { activeRoles } from '../app/permissions.js';
import { navigate } from '../app/router.js';
import { store } from '../app/store.js';
import { icon } from './icons.js';
import { h, initials } from '../utils/dom.js';

function shouldHandleNavigation(event: MouseEvent): boolean {
  const anchor = event.currentTarget as HTMLAnchorElement;
  return !event.defaultPrevented
    && event.button === 0
    && !event.metaKey
    && !event.ctrlKey
    && !event.shiftKey
    && !event.altKey
    && !anchor.target
    && !anchor.hasAttribute('download')
    && anchor.origin === location.origin;
}

/**
 * Family and student accounts do not share the staff product navigation or
 * its organization/school scopes. Portal authorization remains relationship-
 * based in the API, so this shell intentionally does not infer a staff role.
 */
export function createPortalShell(content: HTMLElement): HTMLElement {
  const user = store.state.user;
  const fullName = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.username || 'کاربر';
  const hasStaffWorkspace = activeRoles().length > 0;

  return h(
    'div',
    { className: 'portal-shell' },
    h(
      'header',
      { className: 'portal-shell__header' },
      h(
        'a',
        {
          className: 'portal-shell__brand',
          href: '/portal',
          'aria-label': 'هم‌آموز — پرتال خانواده و دانش‌آموز',
          onClick: (event: MouseEvent) => {
            if (!shouldHandleNavigation(event)) return;
            event.preventDefault();
            navigate('/portal');
          },
        },
        h('span', { className: 'brand__mark', 'aria-hidden': 'true' }, icon('book')),
        h('span', {}, h('strong', { text: 'هم‌آموز' }), h('small', { text: 'پرتال خانواده و دانش‌آموز' })),
      ),
      h(
        'div',
        { className: 'portal-shell__actions' },
        hasStaffWorkspace ? h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate('/') }, 'پنل کارکنان') : null,
        h('span', { className: 'avatar', 'aria-hidden': 'true', text: initials(fullName) }),
        h('span', { className: 'portal-shell__account' }, h('strong', { text: fullName }), h('small', { text: user?.username ?? '' })),
        h('button', {
          className: 'icon-button',
          type: 'button',
          title: 'خروج از حساب',
          'aria-label': 'خروج از حساب',
          onClick: () => void import('../app/auth.js').then(module => module.logout()),
        }, icon('logout')),
      ),
    ),
    h('main', { className: 'portal-shell__main', id: 'page-content', tabindex: '-1' }, content),
  );
}
