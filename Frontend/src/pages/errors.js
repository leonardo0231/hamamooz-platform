import { html } from '../core/view.js';
import { navigate } from '../core/router.js';
import { Button } from '../components/ui.js';
import { Icon } from '../components/icons.js';

export function ErrorPage({ forbidden = false }) {
  return html`<div class="error-page"><span><${Icon} name=${forbidden ? 'shield' : 'search'} size=${42}/></span><p class="eyebrow">${forbidden ? 'خطای ۴۰۳' : 'خطای ۴۰۴'}</p><h1>${forbidden ? 'دسترسی به این بخش مجاز نیست' : 'این صفحه پیدا نشد'}</h1><p>${forbidden ? 'نقش فعال شما مجوز مشاهده این بخش را ندارد.' : 'ممکن است آدرس تغییر کرده باشد یا صفحه حذف شده باشد.'}</p><${Button} onClick=${() => navigate('/')}>بازگشت به داشبورد</${Button}></div>`;
}
