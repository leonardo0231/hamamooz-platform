import { useCallback, useEffect, useState } from "react";

import { api, formatApiError } from "../api";
import { Badge, Card, EmptyState, ErrorBanner, PageTitle, Spinner, dateFa, numberFa, statusFa } from "../components";
import { Icon } from "../icons";

const metrics = [
  { key: "students", title: "دانش‌آموز فعال", icon: "students", tone: "blue" },
  { key: "classes", title: "کلاس فعال", icon: "classes", tone: "violet" },
  { key: "teachers", title: "دبیر فعال", icon: "user", tone: "green" },
  { key: "missing_scores", title: "نمره تکمیل‌نشده", icon: "alert", tone: "orange" },
];

const actionLabels = {
  "auth.login": "ورود به سامانه",
  "auth.logout": "خروج از سامانه",
  create: "ایجاد رکورد",
  update: "ویرایش رکورد",
  delete: "حذف رکورد",
  "assessment.created": "ایجاد ارزیابی",
  "assessment.submitted": "ارسال ارزیابی",
  "assessment.approved": "تأیید ارزیابی",
  "assessment.locked": "قفل ارزیابی",
  "report.queued": "درخواست گزارش",
};

export default function DashboardPage({ refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await api("/dashboard/summary/"));
    } catch (requestError) {
      setError(formatApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <>
      <PageTitle title="داشبورد" description="نمای کلی وضعیت آموزشی شعبه انتخاب‌شده">
        <button className="button button-secondary" type="button" onClick={load} disabled={loading}>
          <Icon name="refresh" size={18} /> تازه‌سازی
        </button>
      </PageTitle>
      <ErrorBanner message={error} onRetry={load} />
      {loading && !data ? (
        <Spinner />
      ) : data ? (
        <>
          <div className="metric-grid">
            {metrics.map((item) => (
              <Card className="metric-card" key={item.key}>
                <span className={`metric-icon metric-${item.tone}`}><Icon name={item.icon} /></span>
                <div><span>{item.title}</span><strong>{numberFa.format(data.counts?.[item.key] || 0)}</strong></div>
              </Card>
            ))}
          </div>

          <div className="dashboard-grid">
            <Card>
              <div className="card-heading"><div><h2>گردش ارزیابی‌ها</h2><p>تعداد ارزیابی در هر مرحله</p></div></div>
              <div className="workflow-list">
                {["draft", "submitted", "rejected", "approved", "locked"].map((status) => (
                  <div className="workflow-row" key={status}>
                    <Badge value={status} />
                    <div className="workflow-track"><span style={{ width: `${Math.min((data.assessment_workflow?.[status] || 0) * 12, 100)}%` }} /></div>
                    <strong>{numberFa.format(data.assessment_workflow?.[status] || 0)}</strong>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <div className="card-heading"><div><h2>دانش‌آموزان شعب</h2><p>توزیع ثبت‌نام فعال</p></div></div>
              {data.students_by_school?.length ? (
                <div className="school-bars">
                  {data.students_by_school.slice(0, 8).map((row) => {
                    const max = Math.max(...data.students_by_school.map((item) => item.students), 1);
                    return <div className="school-bar" key={row.school_id}><span>{row.school__name}</span><div><i style={{ width: `${(row.students / max) * 100}%` }} /></div><strong>{numberFa.format(row.students)}</strong></div>;
                  })}
                </div>
              ) : <EmptyState title="هنوز ثبت‌نام فعالی وجود ندارد" />}
            </Card>

            <Card className="wide-card">
              <div className="card-heading"><div><h2>میانگین کلاس‌ها</h2><p>آخرین نتایج محاسبه‌شده</p></div></div>
              {data.class_averages?.length ? (
                <div className="class-average-grid">
                  {data.class_averages.slice(0, 8).map((row) => (
                    <div className="average-item" key={row.enrollment__class_section_id}>
                      <span>{row.enrollment__class_section__title}</span>
                      <strong>{row.average == null ? "—" : numberFa.format(Number(row.average).toFixed(2))}</strong>
                      <small>{numberFa.format(row.students)} دانش‌آموز</small>
                    </div>
                  ))}
                </div>
              ) : <EmptyState title="هنوز نتیجه‌ای محاسبه نشده است" description="پس از قفل ارزیابی، میانگین کلاس در این بخش نمایش داده می‌شود." />}
            </Card>

            <Card className="wide-card">
              <div className="card-heading"><div><h2>آخرین فعالیت‌ها</h2><p>رویدادهای Audit در محدوده دسترسی شما</p></div></div>
              {data.latest_activities?.length ? (
                <div className="activity-list">
                  {data.latest_activities.map((row) => (
                    <div className="activity-row" key={row.id}>
                      <span className="activity-dot" />
                      <div><strong>{actionLabels[row.action] || row.action}</strong><small>{row.entity_type || "رویداد سامانه"}</small></div>
                      <time>{dateFa(row.created_at, true)}</time>
                    </div>
                  ))}
                </div>
              ) : <EmptyState title="فعالیتی ثبت نشده است" />}
            </Card>
          </div>
        </>
      ) : null}
    </>
  );
}
