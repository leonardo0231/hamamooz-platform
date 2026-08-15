import { html } from '../core/view.js';
import { useStore, roleLabels, activeRoles } from '../core/store.js';
import { Avatar, Button, Card, PageHeader } from '../components/ui.js';

export function ProfilePage() {
  const user = useStore(state => state.user);
  const name = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.username;
  return html`<div class="page"><${PageHeader} title="پروفایل کاربری" subtitle="اطلاعات حساب و تنظیمات امنیتی"/><div class="profile-grid"><${Card} className="profile-card"><${Avatar} name=${name} size="xl"/><h2>${name}</h2><p>${roleLabels[activeRoles()[0]] ?? 'کاربر سامانه'}</p><small>${user?.email}</small></${Card}><${Card} title="اطلاعات حساب"><form class="settings-form"><label>نام<input value=${user?.first_name ?? ''}/></label><label>نام خانوادگی<input value=${user?.last_name ?? ''}/></label><label>ایمیل<input value=${user?.email ?? ''} type="email"/></label><label>شماره تماس<input placeholder="۰۹۱۲۱۲۳۴۵۶۷"/></label><div><${Button}>ذخیره تغییرات</${Button}></div></form></${Card}></div></div>`;
}
