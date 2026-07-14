import { useEffect, useMemo, useState } from "react";

import { API_ROOT, api, clearSession, formatApiError, getSelectedSchool, getTokens, login, logout, setSelectedSchool } from "./api";
import { ErrorBanner, Spinner } from "./components";
import { Icon } from "./icons";
import DashboardPage from "./pages/DashboardPage";
import { AssessmentsPage, ClassesPage, ImportsPage, ReportsPage, StudentsPage } from "./pages/ListPages";

const navigation = [
  { id: "dashboard", label: "داشبورد", icon: "dashboard" },
  { id: "students", label: "دانش‌آموزان", icon: "students" },
  { id: "classes", label: "کلاس‌ها", icon: "classes" },
  { id: "assessments", label: "ارزیابی‌ها", icon: "assessment" },
  { id: "reports", label: "گزارش‌ها", icon: "reports" },
  { id: "imports", label: "ورود اطلاعات", icon: "imports" },
];

const roleLabels = {
  system_admin: "مدیر کل سامانه",
  organization_admin: "مدیر مجموعه",
  school_manager: "مدیر شعبه",
  educational_deputy: "معاون آموزشی",
  operator: "کاربر اجرایی",
  teacher: "دبیر",
};

function LoginPage({ onSuccess }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username.trim(), password);
      onSuccess();
    } catch (requestError) {
      setError(formatApiError(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-decoration decoration-one" />
      <div className="login-decoration decoration-two" />
      <section className="login-card">
        <div className="brand-login"><span>هـ</span><div><strong>هم‌آموز</strong><small>سامانه یکپارچه مدیریت مدارس</small></div></div>
        <div className="login-heading"><h1>ورود به پنل مدیریت</h1><p>برای مشاهده نسخه اولیه، با حساب ساخته‌شده توسط دستور seed وارد شوید.</p></div>
        <form onSubmit={submit} className="login-form">
          <label><span>نام کاربری</span><div className="input-wrap"><Icon name="user" size={19} /><input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></div></label>
          <label><span>رمز عبور</span><div className="input-wrap"><span className="lock-symbol">••</span><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="رمز تعیین‌شده هنگام seed" required /></div></label>
          <ErrorBanner message={error} />
          <button className="button button-primary login-button" type="submit" disabled={loading}>{loading ? <><span className="spinner spinner-light" /> در حال ورود...</> : "ورود به سامانه"}</button>
        </form>
        <div className="login-note"><span className="connection-dot" /> آدرس API: <code>{API_ROOT}</code></div>
      </section>
      <p className="login-footer">نسخه اولیه برای بررسی امکانات MVP</p>
    </main>
  );
}

function PageContent({ page, refreshKey }) {
  const props = { refreshKey };
  if (page === "students") return <StudentsPage {...props} />;
  if (page === "classes") return <ClassesPage {...props} />;
  if (page === "assessments") return <AssessmentsPage {...props} />;
  if (page === "reports") return <ReportsPage {...props} />;
  if (page === "imports") return <ImportsPage {...props} />;
  return <DashboardPage {...props} />;
}

function Shell({ user, schools, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [school, setSchool] = useState(getSelectedSchool());
  const [refreshKey, setRefreshKey] = useState(0);
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;
  const role = user.role_assignments?.find((item) => item.is_active)?.role;
  const initials = displayName.slice(0, 1);

  function selectPage(id) { setPage(id); setMobileOpen(false); }
  function changeSchool(event) { const id = event.target.value; setSchool(id); setSelectedSchool(id); setRefreshKey((value) => value + 1); }

  return (
    <div className="app-shell">
      {mobileOpen && <button className="sidebar-backdrop" type="button" aria-label="بستن منو" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand"><span>هـ</span><div><strong>هم‌آموز</strong><small>مدیریت مدارس</small></div><button className="mobile-close" type="button" onClick={() => setMobileOpen(false)}><Icon name="close" /></button></div>
        <nav aria-label="منوی اصلی">
          <small className="nav-caption">منوی مدیریت</small>
          {navigation.map((item) => <button type="button" className={page === item.id ? "active" : ""} key={item.id} onClick={() => selectPage(item.id)}><Icon name={item.icon} /><span>{item.label}</span><Icon name="chevron" size={16} /></button>)}
        </nav>
        <div className="sidebar-bottom">
          <a href={`${API_ROOT.replace("/api/v1", "")}/api/v1/docs/`} target="_blank" rel="noreferrer"><Icon name="external" size={18} /> مستندات Swagger</a>
          <div className="user-card"><span className="avatar">{initials}</span><div><strong>{displayName}</strong><small>{roleLabels[role] || "کاربر سامانه"}</small></div><button type="button" onClick={onLogout} title="خروج"><Icon name="logout" size={19} /></button></div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button className="mobile-menu" type="button" onClick={() => setMobileOpen(true)}><Icon name="menu" /></button>
          <div className="school-selector"><Icon name="school" size={20} /><label><small>شعبه فعال</small><select value={school} onChange={changeSchool}><option value="">همه شعب مجاز</option>{schools.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label></div>
          <div className="topbar-user"><span><strong>{displayName}</strong><small>{roleLabels[role] || user.username}</small></span><span className="avatar">{initials}</span></div>
        </header>
        <main className="content"><PageContent page={page} refreshKey={refreshKey} /></main>
      </div>
    </div>
  );
}

export default function App() {
  const [state, setState] = useState(getTokens() ? "loading" : "guest");
  const [user, setUser] = useState(null);
  const [schools, setSchools] = useState([]);

  async function bootstrap() {
    setState("loading");
    try {
      const me = await api("/auth/me/");
      const schoolData = await api("/schools/?page_size=200");
      setUser(me);
      setSchools(schoolData.results || schoolData || []);
      const selected = getSelectedSchool();
      if (selected && !(schoolData.results || []).some((item) => item.id === selected)) setSelectedSchool("");
      setState("ready");
    } catch {
      clearSession();
      setState("guest");
    }
  }

  useEffect(() => { if (getTokens()) bootstrap(); }, []);
  const content = useMemo(() => {
    if (state === "loading") return <div className="boot-page"><div className="brand-mark">هـ</div><Spinner label="در حال آماده‌سازی پنل..." /></div>;
    if (state === "guest") return <LoginPage onSuccess={bootstrap} />;
    return <Shell user={user} schools={schools} onLogout={async () => { try { await logout(); } finally { setState("guest"); } }} />;
  }, [state, user, schools]);
  return content;
}
