import { Icon } from "./icons";

const statusLabels = {
  active: "فعال",
  inactive: "غیرفعال",
  draft: "پیش‌نویس",
  submitted: "در انتظار تأیید",
  rejected: "ردشده",
  approved: "تأییدشده",
  locked: "قفل‌شده",
  queued: "در صف",
  processing: "در حال پردازش",
  completed: "تکمیل‌شده",
  failed: "ناموفق",
  transferred: "منتقل‌شده",
  withdrawn: "انصراف‌داده",
  graduated: "فارغ‌التحصیل",
};

export const numberFa = new Intl.NumberFormat("fa-IR");

export function dateFa(value, withTime = false) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("fa-IR", {
      dateStyle: "medium",
      ...(withTime ? { timeStyle: "short" } : {}),
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function statusFa(value) {
  return statusLabels[value] || value || "—";
}

export function Spinner({ label = "در حال دریافت اطلاعات..." }) {
  return (
    <div className="state-box" role="status">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title = "داده‌ای ثبت نشده است", description }) {
  return (
    <div className="state-box empty-state">
      <span className="empty-icon">⌁</span>
      <strong>{title}</strong>
      {description && <span>{description}</span>}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="error-banner" role="alert">
      <Icon name="alert" />
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="text-button" onClick={onRetry}>
          تلاش دوباره
        </button>
      )}
    </div>
  );
}

export function Badge({ value, label }) {
  return <span className={`badge badge-${value || "neutral"}`}>{label || statusFa(value)}</span>;
}

export function PageTitle({ title, description, children }) {
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children && <div className="page-actions">{children}</div>}
    </div>
  );
}

export function SearchBar({ value, onChange, onSubmit, placeholder = "جست‌وجو...", loading }) {
  return (
    <form className="search-bar" onSubmit={onSubmit}>
      <Icon name="search" size={19} />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
      />
      <button className="button button-secondary button-small" type="submit" disabled={loading}>
        جست‌وجو
      </button>
    </form>
  );
}

export function Card({ children, className = "" }) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function TableShell({ children }) {
  return <div className="table-shell">{children}</div>;
}
