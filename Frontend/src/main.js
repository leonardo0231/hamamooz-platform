import { html, render, useEffect } from './core/view.js';
import { restoreSession } from './core/api.js';
import { navigate, useRoute } from './core/router.js';
import { hasRole, useStore } from './core/store.js';
import { Shell } from './components/shell.js';
import { Skeleton } from './components/ui.js';
import { DashboardPage } from './pages/dashboard.js';
import { StudentsPage } from './pages/students.js';
import { StudentPage } from './pages/student.js';
import { AlertsPage } from './pages/alerts.js';
import { GenericPage } from './pages/generic.js';
import { LoginPage } from './pages/login.js';
import { ProfilePage } from './pages/profile.js';
import { ReportsPage } from './pages/reports.js';
import { ImportsPage } from './pages/imports.js';
import { ErrorPage } from './pages/errors.js';

function Page({ route }) {
  switch (route.id) {
    case 'dashboard': return html`<${DashboardPage}/>`;
    case 'students': return html`<${StudentsPage}/>`;
    case 'student': return html`<${StudentPage} id=${route.params.id}/>`;
    case 'alerts': return html`<${AlertsPage}/>`;
    case 'profile': return html`<${ProfilePage}/>`;
    case 'reports': return html`<${ReportsPage}/>`;
    case 'imports': return html`<${ImportsPage}/>`;
    case 'not-found': return html`<${ErrorPage}/>`;
    case 'forbidden': return html`<${ErrorPage} forbidden=${true}/>`;
    case 'resource': return html`<${GenericPage} kind="resource" tag=${route.params.tag}/>`;
    default: return html`<${GenericPage} kind=${route.id}/>`;
  }
}

function App() {
  const route = useRoute();
  const { user, bootstrapping } = useStore(state => ({ user: state.user, bootstrapping: state.bootstrapping }));
  useEffect(() => { void restoreSession(); }, []);
  useEffect(() => { document.title = `${route.title} | هم‌آموز`; }, [route.title]);
  useEffect(() => {
    if (!bootstrapping && !user && !route.public) navigate(`/login?returnTo=${encodeURIComponent(location.pathname)}`, true);
    if (!bootstrapping && user && route.id === 'login') navigate('/', true);
    if (!bootstrapping && user && route.roles && !hasRole(route.roles)) navigate('/forbidden', true);
    if (!bootstrapping && user?.must_change_password && route.id !== 'profile') navigate('/profile?passwordRequired=1', true);
  }, [bootstrapping, user, route.id, route.roles]);

  if (bootstrapping) return html`<main class="boot-screen"><div class="boot-screen__logo">هـ</div><${Skeleton} lines=${3}/></main>`;
  if (route.id === 'login') return html`<${LoginPage}/>`;
  if (!user) return html`<main class="boot-screen"><${Skeleton} lines=${3}/></main>`;
  return html`<${Shell} route=${route}><${Page} route=${route}/></${Shell}>`;
}

const root = document.querySelector('#app');
if (!root) throw new Error('Application root was not found.');
render(html`<${App}/>`, root);
