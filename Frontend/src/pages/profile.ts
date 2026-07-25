import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { operationById } from '../api/contract.js';
import { actionRequestSchema } from '../api/action-schemas.js';
import { store } from '../app/store.js';
import { navigate } from '../app/router.js';
import { activeRoles, roleLabel } from '../app/permissions.js';
import { h, formatDate, initials } from '../utils/dom.js';
import { toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { openSchemaDialog } from '../components/schema-form.js';

export function renderProfilePage(): HTMLElement {
  const user = store.state.user;
  if (!user) return h('section', { className: 'page' });
  const fullName = `${user.first_name} ${user.last_name}`.trim() || user.username;
  const changePassword = (): void => {
    const operation = operationById('users_change_password_create');
    if (!operation) return;
    openSchemaDialog({
      title: 'تغییر رمز عبور',
      schema: { ...actionRequestSchema(operation), required: ['current_password', 'new_password'] },
      submitLabel: 'تغییر رمز',
      onSubmit: async payload => {
        await apiRequest(endpoints.users.changePassword(user.id), { method: 'POST', body: payload, responseType: 'void' });
        store.clearSession();
        toast('رمز عبور تغییر کرد. برای ادامه دوباره وارد شوید.', 'success');
        navigate('/login', true);
      },
    });
  };
  const accountCard = h('article', { className: 'card' },
    h('div', { className: 'card-header' }, h('h2', { text: 'اطلاعات حساب' }), h('span', { className: 'card-icon' }, icon('user'))),
    h('dl', { className: 'detail-grid' },
      h('div', {}, h('dt', { text: 'نام کاربری' }), h('dd', { text: user.username })),
      h('div', {}, h('dt', { text: 'ایمیل' }), h('dd', { text: user.email })),
      h('div', {}, h('dt', { text: 'تلفن' }), h('dd', { text: user.phone || '—' })),
      h('div', {}, h('dt', { text: 'آخرین ورود' }), h('dd', { text: formatDate(user.last_login, true) })),
      h('div', {}, h('dt', { text: 'وضعیت' }), h('dd', {}, h('span', { className: `badge badge--${user.is_active ? 'success' : 'danger'}`, text: user.is_active ? 'فعال' : 'غیرفعال' }))),
    ),
  );
  const assignmentItems = user.role_assignments.filter(item => item.is_active).map(item =>
    h('div', { className: 'assignment-item' },
      h('span', { className: 'assignment-item__icon' }, icon(item.school ? 'building' : 'settings')),
      h('div', {}, h('strong', { text: item.role_display ?? roleLabel(item.role) }), h('small', { className: 'ltr', text: item.school ? `School: ${item.school}` : item.organization ? `Organization: ${item.organization}` : 'Global' })),
    ),
  );
  const assignmentsCard = h('article', { className: 'card' },
    h('div', { className: 'card-header' }, h('h2', { text: 'حوزه‌ها و نقش‌ها' }), h('span', { className: 'card-icon' }, icon('settings'))),
    h('div', { className: 'assignment-list' }, ...assignmentItems),
  );
  const passwordRequired = Boolean(user.must_change_password || new URLSearchParams(location.search).has('passwordRequired'));
  return h('section', { className: 'page' },
    h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'حساب کاربری' }), h('h1', { text: 'پروفایل من' }), h('p', { text: 'اطلاعات نشست از endpoint احراز هویت دریافت شده است.' })), h('button', { className: 'button button--primary', type: 'button', onClick: changePassword }, icon('settings'), 'تغییر رمز عبور')),
    passwordRequired ? h('article', { className: 'contract-notice contract-notice--warning', role: 'alert' }, icon('warning'), h('div', {}, h('strong', { text: 'تغییر رمز عبور الزامی است' }), h('p', { text: 'پیش از استفاده از سایر بخش‌های سامانه، رمز موقت حساب را تغییر دهید.' }))) : null,
    h('article', { className: 'profile-card card' }, h('span', { className: 'profile-avatar', text: initials(fullName) }), h('div', {}, h('h2', { text: fullName }), h('p', { text: user.email }), h('div', { className: 'badge-row' }, ...activeRoles().map(role => h('span', { className: 'badge badge--neutral', text: roleLabel(role) }))))),
    h('div', { className: 'profile-grid' }, accountCard, assignmentsCard),
  );

}
