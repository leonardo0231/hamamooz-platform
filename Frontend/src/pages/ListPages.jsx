import { useCallback, useEffect, useState } from "react";

import { api, download, formatApiError, getSelectedSchool } from "../api";
import { Badge, Card, EmptyState, ErrorBanner, PageTitle, SearchBar, Spinner, TableShell, dateFa, numberFa } from "../components";
import { Icon } from "../icons";

function useList(path, refreshKey) {
  const [rows, setRows] = useState([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const separator = path.includes("?") ? "&" : "?";
      const data = await api(`${path}${separator}page_size=200${query ? `&search=${encodeURIComponent(query)}` : ""}`);
      setRows(data.results || data || []);
      setCount(data.count ?? data.length ?? 0);
    } catch (requestError) {
      setError(formatApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, [path, query]);

  useEffect(() => { load(); }, [load, refreshKey]);
  const submit = (event) => { event.preventDefault(); setQuery(search.trim()); };
  return { rows, count, search, setSearch, loading, error, load, submit };
}

function ListHeader({ title, description, list, placeholder }) {
  return (
    <>
      <PageTitle title={title} description={description}>
        <span className="result-count">{numberFa.format(list.count)} رکورد</span>
        <button className="icon-button" type="button" onClick={list.load} aria-label="تازه‌سازی"><Icon name="refresh" size={18} /></button>
      </PageTitle>
      <SearchBar value={list.search} onChange={list.setSearch} onSubmit={list.submit} placeholder={placeholder} loading={list.loading} />
      <ErrorBanner message={list.error} onRetry={list.load} />
    </>
  );
}

export function StudentsPage({ refreshKey }) {
  const list = useList("/enrollments/", refreshKey);
  return <><ListHeader title="دانش‌آموزان" description="ثبت‌نام‌ها و کلاس‌بندی فعال" list={list} placeholder="نام، کد ملی یا شماره دانش‌آموزی" />
    <Card className="table-card">{list.loading && !list.rows.length ? <Spinner /> : list.rows.length ? <TableShell><table><thead><tr><th>دانش‌آموز</th><th>شماره</th><th>پایه</th><th>کلاس</th><th>شعبه</th><th>وضعیت</th><th>تاریخ ثبت‌نام</th></tr></thead><tbody>{list.rows.map((row) => <tr key={row.id}><td><strong>{row.student_name}</strong></td><td>{row.student_number || "—"}</td><td>{row.grade_title}</td><td>{row.class_title}</td><td>{row.school_name}</td><td><Badge value={row.status} /></td><td>{dateFa(row.enrolled_on)}</td></tr>)}</tbody></table></TableShell> : <EmptyState title="دانش‌آموزی برای نمایش وجود ندارد" description="پس از Import یا ثبت‌نام، اطلاعات اینجا نمایش داده می‌شود." />}</Card>
  </>;
}

export function ClassesPage({ refreshKey }) {
  const list = useList("/classes/", refreshKey);
  return <><ListHeader title="کلاس‌ها" description="ظرفیت و تعداد ثبت‌نام کلاس‌ها" list={list} placeholder="عنوان یا کد کلاس" />
    <Card className="table-card">{list.loading && !list.rows.length ? <Spinner /> : list.rows.length ? <TableShell><table><thead><tr><th>عنوان کلاس</th><th>کد</th><th>ثبت‌نام</th><th>ظرفیت</th><th>درصد تکمیل</th><th>وضعیت</th></tr></thead><tbody>{list.rows.map((row) => { const enrolled = row.enrolled_count || 0; const percent = row.capacity ? Math.min((enrolled / row.capacity) * 100, 100) : 0; return <tr key={row.id}><td><strong>{row.title}</strong></td><td>{row.code}</td><td>{numberFa.format(enrolled)}</td><td>{numberFa.format(row.capacity)}</td><td><div className="capacity"><span><i style={{ width: `${percent}%` }} /></span><small>{numberFa.format(Math.round(percent))}٪</small></div></td><td><Badge value={row.is_active ? "active" : "inactive"} /></td></tr>; })}</tbody></table></TableShell> : <EmptyState title="کلاسی یافت نشد" />}</Card>
  </>;
}

export function AssessmentsPage({ refreshKey }) {
  const list = useList("/assessments/", refreshKey);
  const [busy, setBusy] = useState("");
  const [actionError, setActionError] = useState("");

  async function runAction(row, action) {
    let body;
    if (action === "reject") {
      const reason = window.prompt("دلیل رد ارزیابی را وارد کنید:");
      if (!reason) return;
      body = JSON.stringify({ reason });
    }
    setBusy(`${row.id}:${action}`);
    setActionError("");
    try {
      await api(`/assessments/${row.id}/${action}/`, { method: "POST", ...(body ? { body } : {}) });
      await list.load();
    } catch (requestError) {
      setActionError(formatApiError(requestError));
    } finally { setBusy(""); }
  }

  const actions = (row) => {
    if (["draft", "rejected"].includes(row.status)) return [["submit", "ارسال برای تأیید"]];
    if (row.status === "submitted") return [["approve", "تأیید"], ["reject", "رد"]];
    if (row.status === "approved") return [["lock", "قفل نهایی"]];
    return [];
  };

  return <><ListHeader title="ارزیابی‌ها" description="مشاهده و بررسی گردش ثبت نمرات" list={list} placeholder="عنوان، درس یا کلاس" /><ErrorBanner message={actionError} />
    <Card className="table-card">{list.loading && !list.rows.length ? <Spinner /> : list.rows.length ? <TableShell><table><thead><tr><th>ارزیابی</th><th>درس و کلاس</th><th>دبیر</th><th>تاریخ</th><th>نمرات</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>{list.rows.map((row) => <tr key={row.id}><td><strong>{row.title}</strong><small>{row.assessment_type_title}</small></td><td>{row.subject_title}<small>{row.class_title}</small></td><td>{row.teacher_name || "—"}</td><td>{dateFa(row.assessment_date)}</td><td>{numberFa.format(row.score_count || 0)}</td><td><Badge value={row.status} /></td><td><div className="table-actions">{actions(row).map(([key, label]) => <button className={`button button-small ${key === "reject" ? "button-danger" : "button-secondary"}`} type="button" key={key} disabled={Boolean(busy)} onClick={() => runAction(row, key)}>{busy === `${row.id}:${key}` ? "..." : label}</button>)}{!actions(row).length && <span>—</span>}</div></td></tr>)}</tbody></table></TableShell> : <EmptyState title="ارزیابی‌ای ثبت نشده است" />}</Card>
  </>;
}

export function ReportsPage({ refreshKey }) {
  const list = useList("/reports/", refreshKey);
  const [fileError, setFileError] = useState("");
  async function getFile(row) { setFileError(""); try { await download(`/reports/${row.id}/download/`, `hamamooz-report-${row.id}.pdf`); } catch (error) { setFileError(formatApiError(error)); } }
  return <><ListHeader title="گزارش‌ها و کارنامه‌ها" description="آرشیو خروجی‌های رسمی تولیدشده" list={list} placeholder="جست‌وجوی گزارش" /><ErrorBanner message={fileError} />
    <Card className="table-card">{list.loading && !list.rows.length ? <Spinner /> : list.rows.length ? <TableShell><table><thead><tr><th>نوع گزارش</th><th>درخواست‌دهنده</th><th>نسخه فرمول</th><th>زمان درخواست</th><th>وضعیت</th><th>فایل</th></tr></thead><tbody>{list.rows.map((row) => <tr key={row.id}><td><strong>{row.report_type === "student_report_card" ? "کارنامه دانش‌آموز" : "کارنامه گروهی کلاس"}</strong></td><td>{row.requested_by_name || "—"}</td><td>{row.formula_version || "—"}</td><td>{dateFa(row.created_at, true)}</td><td><Badge value={row.status} label={row.status_display} /></td><td>{row.status === "completed" ? <button className="button button-secondary button-small" type="button" onClick={() => getFile(row)}><Icon name="download" size={16} /> دریافت PDF</button> : "—"}</td></tr>)}</tbody></table></TableShell> : <EmptyState title="هنوز گزارشی تولید نشده است" description="گزارش‌های رسمی پس از قفل کامل ارزیابی‌ها قابل تولید هستند." />}</Card>
  </>;
}

export function ImportsPage({ refreshKey }) {
  const list = useList("/imports/", refreshKey);
  const [type, setType] = useState("students");
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const school = getSelectedSchool();
  async function submit(event) {
    event.preventDefault(); setMessage(""); setUploadError("");
    if (!school) { setUploadError("برای Import ابتدا یک شعبه مشخص انتخاب کنید."); return; }
    if (!file) { setUploadError("یک فایل XLSX انتخاب کنید."); return; }
    const form = new FormData(); form.append("school", school); form.append("import_type", type); form.append("source_file", file);
    setUploading(true);
    try { await api("/imports/", { method: "POST", body: form }); setMessage("فایل با موفقیت در صف پردازش قرار گرفت."); setFile(null); event.currentTarget.reset(); await list.load(); }
    catch (error) { setUploadError(formatApiError(error)); }
    finally { setUploading(false); }
  }
  return <><PageTitle title="ورود اطلاعات Excel" description="بارگذاری فایل‌های ثابت و مشاهده نتیجه پردازش" />
    <div className="import-layout"><Card><div className="card-heading"><div><h2>فایل جدید</h2><p>فقط قالب XLSX استاندارد سامانه</p></div></div><form className="upload-form" onSubmit={submit}><label><span>نوع اطلاعات</span><select value={type} onChange={(event) => setType(event.target.value)}><option value="students">دانش‌آموزان</option><option value="enrollments">ثبت‌نام و کلاس‌بندی</option><option value="scores">نمرات اولیه</option></select></label><label className="file-picker"><Icon name="upload" /><span>{file?.name || "انتخاب فایل XLSX"}</span><input type="file" accept=".xlsx" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="button button-primary" type="submit" disabled={uploading}>{uploading ? "در حال ارسال..." : "ارسال برای پردازش"}</button><ErrorBanner message={uploadError} />{message && <div className="success-banner">{message}</div>}<small className="form-hint">حداکثر حجم فایل ۱۰ مگابایت است و در صورت وجود خطا هیچ ردیفی ذخیره نمی‌شود.</small></form></Card>
      <Card><div className="card-heading"><div><h2>راهنمای سریع</h2><p>ترتیب پیشنهادی ورود اطلاعات</p></div></div><ol className="step-list"><li><span>۱</span><div><strong>دانش‌آموزان</strong><small>مشخصات پایه و کد ملی</small></div></li><li><span>۲</span><div><strong>ثبت‌نام‌ها</strong><small>سال، پایه و کلاس‌بندی</small></div></li><li><span>۳</span><div><strong>نمرات</strong><small>شناسه ارزیابی و مقدار نمره</small></div></li></ol></Card></div>
    <div className="section-space"><ListHeader title="سوابق Import" description="آخرین Jobهای پردازش فایل" list={list} placeholder="جست‌وجو" /><Card className="table-card">{list.loading && !list.rows.length ? <Spinner /> : list.rows.length ? <TableShell><table><thead><tr><th>نوع</th><th>درخواست‌دهنده</th><th>کل ردیف</th><th>موفق</th><th>خطا</th><th>وضعیت</th><th>زمان</th></tr></thead><tbody>{list.rows.map((row) => <tr key={row.id}><td><strong>{{ students: "دانش‌آموزان", enrollments: "ثبت‌نام‌ها", scores: "نمرات" }[row.import_type]}</strong></td><td>{row.requested_by_name || "—"}</td><td>{numberFa.format(row.total_rows || 0)}</td><td>{numberFa.format(row.successful_rows || 0)}</td><td>{numberFa.format(row.error_count || 0)}</td><td><Badge value={row.status} label={row.status_display} /></td><td>{dateFa(row.created_at, true)}</td></tr>)}</tbody></table></TableShell> : <EmptyState title="سابقه Import وجود ندارد" />}</Card></div>
  </>;
}
