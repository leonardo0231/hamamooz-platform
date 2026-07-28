import { navigate } from '../app/router.js';
import { h } from '../utils/dom.js';
import { icon } from '../components/icons.js';

function errorPage(code: string, title: string, description: string): HTMLElement {
  return h('section', { className: 'error-page' }, h('div', { className: 'error-page__visual' }, icon('warning')), h('span', { className: 'error-code', text: code }), h('h1', { text: title }), h('p', { text: description }), h('button', { className: 'button button--primary', type: 'button', onClick: () => navigate('/') }, icon('home'), 'بازگشت به داشبورد'));
}
export function renderForbiddenPage(): HTMLElement { return errorPage('403', 'دسترسی مجاز نیست', 'نقش فعلی یا حوزه انتخاب‌شده اجازه مشاهده این صفحه را ندارد.'); }
export function renderNotFoundPage(): HTMLElement { return errorPage('404', 'صفحه پیدا نشد', 'آدرس واردشده معتبر نیست یا صفحه موردنظر جابه‌جا شده است.'); }
