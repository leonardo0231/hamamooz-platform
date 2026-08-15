import { html, useState } from '../core/view.js';
import { login } from '../core/api.js';
import { navigate } from '../core/router.js';
import { Button } from '../components/ui.js';
import { Icon } from '../components/icons.js';

export function LoginPage() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const requested = new URLSearchParams(location.search).get('returnTo');
    const returnTo = requested?.startsWith('/') && !requested.startsWith('//') ? requested : '/';
    try { await login(identifier, password, remember); navigate(returnTo, true); }
    catch (value) { setError(value?.message ?? 'ورود ناموفق بود.'); }
    finally { setBusy(false); }
  }
  return html`<main class="login-page"><section class="login-visual"><div class="login-visual__orb login-visual__orb--one"></div><div class="login-visual__orb login-visual__orb--two"></div><div class="login-brand"><span><${Icon} name="graduation" size=${34}/></span><div><strong>هم‌آموز</strong><small>سامانه هوشمند مدیریت مدرسه</small></div></div><div class="login-visual__content"><p>یک تصویر روشن از مدرسه</p><h1>از داده تا تصمیم،<br/>برای رشد هر دانش‌آموز</h1><span>پایش آموزشی، حضور و غیاب، هشدارهای هوشمند و پرونده ۳۶۰ درجه در یک سامانه.</span></div><div class="login-preview"><div><${Icon} name="chart"/><span><small>رشد عملکرد</small><strong>+۶٫۲٪</strong></span></div><div><${Icon} name="attendance"/><span><small>حضور امروز</small><strong>۹۷٪</strong></span></div></div></section>
  <section class="login-form-wrap"><form class="login-form" onSubmit=${submit}><div class="login-form__mark"><${Icon} name="school" size=${27}/></div><p class="eyebrow">خوش آمدید</p><h2>ورود به سامانه هم‌آموز</h2><p>برای ادامه اطلاعات حساب کاربری خود را وارد کنید.</p>${error && html`<div class="form-error" role="alert">${error}</div>`}<label>نام کاربری یا ایمیل<input autocomplete="username" value=${identifier} onInput=${event => setIdentifier(event.currentTarget.value)} required placeholder="نام کاربری خود را وارد کنید"/></label><label>رمز عبور<input type="password" autocomplete="current-password" value=${password} onInput=${event => setPassword(event.currentTarget.value)} required placeholder="••••••••"/></label><div class="login-options"><label><input type="checkbox" checked=${remember} onChange=${event => setRemember(event.currentTarget.checked)}/> مرا به خاطر بسپار</label><button type="button">بازیابی رمز عبور</button></div><${Button} type="submit" className="button--block" disabled=${busy}>${busy ? 'در حال ورود…' : 'ورود به سامانه'}</${Button}><small class="login-help">برای دریافت دسترسی با مدیر سامانه مدرسه تماس بگیرید.</small></form></section></main>`;
}
