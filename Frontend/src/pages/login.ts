import { login } from '../app/auth.js';
import { navigate, postLoginRedirectPath } from '../app/router.js';
import { ApiError } from '../api/types.js';
import { config } from '../app/config.js';
import { h } from '../utils/dom.js';
import { icon } from '../components/icons.js';

export function renderLoginPage(): HTMLElement {
  const identifier = h('input', { id: 'login-identifier', name: 'username', type: 'text', autocomplete: 'username', required: true, placeholder: 'نام کاربری یا ایمیل', dir: 'auto' }) as HTMLInputElement;
  const password = h('input', { id: 'login-password', name: 'password', type: 'password', autocomplete: 'current-password', required: true, placeholder: 'رمز عبور' }) as HTMLInputElement;
  const remember = h('input', { id: 'remember-session', type: 'checkbox' }) as HTMLInputElement;
  const error = h('div', { className: 'form-error', role: 'alert' });
  const submit = h('button', { className: 'button button--primary button--large', type: 'submit' }, 'ورود به سامانه', icon('chevron')) as HTMLButtonElement;
  const form = h('form', { className: 'login-form' },
    h('div', { className: 'form-field' }, h('label', { for: 'login-identifier', text: 'نام کاربری یا ایمیل' }), h('div', { className: 'input-with-icon' }, icon('user'), identifier)),
    h('div', { className: 'form-field' }, h('label', { for: 'login-password', text: 'رمز عبور' }), h('div', { className: 'input-with-icon' }, icon('settings'), password)),
    h('div', { className: 'login-options' }, h('label', { className: 'checkbox-label', for: 'remember-session' }, remember, 'مرا به خاطر بسپار'), h('span', { className: 'muted', text: 'بازیابی رمز در API فعلی ارائه نشده است' })),
    error,
    submit,
  ) as HTMLFormElement;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    error.textContent = '';
    if (!form.reportValidity()) return;
    submit.disabled = true;
    submit.replaceChildren(h('span', { className: 'spinner spinner--small' }), 'در حال ورود…');
    try {
      await login(identifier.value.trim(), password.value, remember.checked);
      const returnTo = new URLSearchParams(location.search).get('returnTo');
      navigate(postLoginRedirectPath(returnTo), true);
    } catch (caught) {
      const apiError = caught instanceof ApiError ? caught : null;
      error.textContent = apiError?.message ?? (caught instanceof Error ? caught.message : 'ورود ناموفق بود.');
      password.focus();
      password.select();
    } finally {
      submit.disabled = false;
      submit.replaceChildren('ورود به سامانه', icon('chevron'));
    }
  });

  return h('main', { className: 'login-page', id: 'page-content', tabindex: '-1' },
    h('section', { className: 'login-visual', 'aria-hidden': 'true' },
      h('div', { className: 'login-orb login-orb--one' }), h('div', { className: 'login-orb login-orb--two' }),
      h('div', { className: 'login-visual__content' }, h('div', { className: 'brand brand--large' }, h('span', { className: 'brand__mark' }, icon('book')), h('div', {}, h('strong', { text: config.appName }), h('small', { text: 'مدیریت هوشمند مدرسه' }))),
        h('h1', { text: 'تصمیم‌گیری آموزشی، با داده‌های واقعی و یکپارچه' }),
        h('p', { text: 'مدیریت دانش‌آموزان، عملکرد تحصیلی، حضور و غیاب، هشدارها و گزارش‌ها در یک فضای امن و منسجم.' }),
        h('div', { className: 'login-feature-grid' },
          h('div', {}, icon('chart'), h('strong', { text: 'تحلیل عملکرد' }), h('small', { text: 'نمای واحد از وضعیت آموزشی' })),
          h('div', {}, icon('bell'), h('strong', { text: 'پیگیری هوشمند' }), h('small', { text: 'هشدارهای قابل اقدام' })),
          h('div', {}, icon('users'), h('strong', { text: 'پرونده یکپارچه' }), h('small', { text: 'اطلاعات معتبر و به‌روز' })),
        ),
      ),
    ),
    h('section', { className: 'login-panel' },
      h('div', { className: 'login-card' }, h('span', { className: 'eyebrow', text: 'ورود امن' }), h('h1', { text: 'خوش آمدید' }), h('p', { text: 'برای ادامه، اطلاعات حساب سازمانی خود را وارد کنید.' }), form,
        h('div', { className: 'login-security' }, icon('check'), h('span', { text: 'Access Token فقط در حافظه نگهداری می‌شود و نشست از طریق Backend اعتبارسنجی خواهد شد.' }))),
    ),
  );
}
