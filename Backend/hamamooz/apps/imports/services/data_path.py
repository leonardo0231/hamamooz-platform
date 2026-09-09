"""Import the repository's mounted ``Data`` directory as one source bundle.

The registrar's directory is intentionally treated as a source tree rather
than as a browser upload.  Every workbook receives its own ImportJob for
provenance, while DataPathImport records the scan, photo reconciliation,
warnings, and report batches created from the complete bundle.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from django.core.files import File
from django.utils import timezone

from hamamooz.apps.organizations.models import AcademicYear
from hamamooz.apps.reports.models import ReportBatch, ReportBatchItem
from hamamooz.apps.students.models import Enrollment

from ..models import DataPathImport, ImportJob
from ..pipeline import process_import_job
from .photo_importer import StudentPhotoImporter

WORKBOOK_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PHOTO_ARCHIVE_EXTENSIONS = {".zip"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_entry(path: Path, root: Path, *, checksum=False) -> dict:
    entry = {
        "path": str(path.relative_to(root)),
        "name": path.name,
        "size": path.stat().st_size,
    }
    if checksum:
        entry["sha256"] = _sha256(path)
    return entry


def discover_data_path(source_root) -> dict:
    """Return a deterministic, read-only manifest of Excel and photo assets."""

    root = Path(source_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"مسیر Data پیدا نشد: {root}")

    excel_root = root / "Excel"
    photo_root = root / "Photo"
    workbook_files = []
    unsupported_excel = []
    if excel_root.is_dir():
        for path in sorted(excel_root.rglob("*"), key=lambda item: str(item).lower()):
            if path.is_symlink() or not path.is_file() or path.name.startswith("~$"):
                continue
            if path.suffix.lower() in WORKBOOK_EXTENSIONS:
                workbook_files.append(path)
            else:
                unsupported_excel.append(_file_entry(path, root))

    photo_files = []
    photo_archives = []
    unsupported_photos = []
    if photo_root.is_dir():
        for path in sorted(photo_root.rglob("*"), key=lambda item: str(item).lower()):
            if path.is_symlink() or not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in PHOTO_EXTENSIONS:
                photo_files.append(path)
            elif suffix in PHOTO_ARCHIVE_EXTENSIONS:
                photo_archives.append(path)
            else:
                unsupported_photos.append(_file_entry(path, root))

    return {
        "source_root": str(root),
        "excel_root": str(excel_root),
        "photo_root": str(photo_root),
        "workbooks": [_file_entry(path, root, checksum=True) for path in workbook_files],
        "photo_files": [_file_entry(path, root) for path in photo_files],
        "photo_archives": [_file_entry(path, root) for path in photo_archives],
        "unsupported_excel": unsupported_excel,
        "unsupported_photos": unsupported_photos,
        "counts": {
            "workbooks": len(workbook_files),
            "photo_files": len(photo_files),
            "photo_archives": len(photo_archives),
            "unsupported_excel": len(unsupported_excel),
            "unsupported_photos": len(unsupported_photos),
        },
    }


def _existing_job(run, checksum):
    return (
        ImportJob.objects.filter(
            organization=run.organization,
            school=run.school,
            import_type=ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
            checksum=checksum,
            status__in=[
                ImportJob.Status.UPLOADED,
                ImportJob.Status.ANALYZING,
                ImportJob.Status.PREVIEW_READY,
                ImportJob.Status.CONFIRMED,
                ImportJob.Status.PROCESSING,
                ImportJob.Status.COMPLETED,
            ],
        )
        .order_by("-created_at")
        .first()
    )


def _create_file_job(run, path, checksum):
    existing = _existing_job(run, checksum)
    if existing is not None:
        return existing, False

    job = ImportJob(
        organization=run.organization,
        school=run.school,
        import_type=ImportJob.ImportType.COMPREHENSIVE_SCHOOL,
        status=ImportJob.Status.QUEUED,
        source_kind=ImportJob.SourceKind.DATA_PATH,
        data_path_import=run,
        checksum=checksum,
        requested_by=run.requested_by,
    )
    with path.open("rb") as source:
        job.source_file.save(path.name, File(source), save=True)
    return job, True


def _merge_photo_results(results):
    merged = {
        "received": 0,
        "matched": 0,
        "missing_students": 0,
        "duplicates": 0,
        "duplicate_files": [],
        "skipped_existing": 0,
        "invalid_files": [],
        "orphans": [],
    }
    for result in results:
        for key in ("received", "matched", "missing_students", "duplicates", "skipped_existing"):
            merged[key] += int(result.get(key, 0) or 0)
        for key in ("duplicate_files", "invalid_files", "orphans"):
            merged[key].extend(result.get(key, []) or [])
    return merged


def _latest_month(school, academic_year):
    from hamamooz.apps.evaluations.models import AssessmentPeriod

    period = (
        AssessmentPeriod.objects.filter(
            academic_year=academic_year,
            records__student__enrollments__school=school,
        )
        .order_by("-order")
        .first()
    )
    return period.order if period else None


def _queue_report_batches(run, academic_year_ids):
    """Create one school-wide monthly batch per imported academic year."""

    from hamamooz.apps.reports.tasks import generate_report_batch_task

    batches = []
    for academic_year in AcademicYear.objects.filter(id__in=academic_year_ids):
        month_no = run.report_month or _latest_month(run.school, academic_year)
        if month_no is None:
            continue
        enrollments = list(
            Enrollment.objects.filter(
                school=run.school,
                academic_year=academic_year,
                status=Enrollment.Status.ACTIVE,
            ).select_related("student")
        )
        if not enrollments:
            continue
        batch = ReportBatch.objects.create(
            organization=run.organization,
            school=run.school,
            academic_year=academic_year,
            term=None,
            report_mode=ReportBatch.ReportMode.DATA_MONTHLY,
            month_no=month_no,
            scope=ReportBatch.Scope.SCHOOL,
            page_size="a3_landscape",
            requested_by=run.requested_by,
            total_count=len(enrollments),
        )
        ReportBatchItem.objects.bulk_create(
            [ReportBatchItem(batch=batch, enrollment=enrollment) for enrollment in enrollments]
        )
        generate_report_batch_task.delay(str(batch.id))
        batches.append(
            {
                "id": str(batch.id),
                "academic_year_id": str(academic_year.id),
                "academic_year": academic_year.title,
                "month_no": month_no,
                "total_count": len(enrollments),
                "status": batch.status,
            }
        )
    return batches


def process_data_path_import(run_id):
    """Scan, import, reconcile photos, and queue monthly report output."""

    run = DataPathImport.objects.select_related("organization", "school", "requested_by").get(
        pk=run_id
    )
    if run.status in {DataPathImport.Status.COMPLETED, DataPathImport.Status.PARTIAL}:
        return run

    run.status = DataPathImport.Status.SCANNING
    run.started_at = timezone.now()
    run.finished_at = None
    run.errors = []
    run.result_summary = {}
    run.save(update_fields=["status", "started_at", "finished_at", "errors", "result_summary", "updated_at"])

    manifest = {}
    errors = []
    child_jobs = []
    imported_year_ids = set()
    try:
        manifest = discover_data_path(run.source_root)
        run.manifest = manifest
        run.status = DataPathImport.Status.PROCESSING
        run.save(update_fields=["manifest", "status", "updated_at"])

        if not Path(manifest["excel_root"]).is_dir():
            errors.append({"phase": "scan", "error": "مسیر Data/Excel پیدا نشد."})
        for entry in [*manifest["unsupported_excel"], *manifest["unsupported_photos"]]:
            errors.append(
                {
                    "phase": "scan",
                    "file": entry["path"],
                    "warning": True,
                    "error": "پسوند فایل توسط Import مستقیم پشتیبانی نمی‌شود؛ فایل در محل اصلی باقی ماند.",
                }
            )

        for workbook_entry in manifest["workbooks"]:
            path = Path(manifest["source_root"]) / workbook_entry["path"]
            try:
                job, created = _create_file_job(run, path, workbook_entry["sha256"])
                if created or job.status in {
                    ImportJob.Status.QUEUED,
                    ImportJob.Status.UPLOADED,
                    ImportJob.Status.FAILED,
                }:
                    job = process_import_job(str(job.id))
                child_jobs.append(job)
                academic_year_id = job.result_summary.get("academic_year_id")
                if academic_year_id:
                    imported_year_ids.add(academic_year_id)
                if job.status == ImportJob.Status.FAILED or job.error_count:
                    errors.extend(
                        {
                            "phase": "excel",
                            "file": workbook_entry["path"],
                            "job_id": str(job.id),
                            "error": item,
                        }
                        for item in (job.errors or [])[:100]
                    )
            except Exception as exc:  # one malformed workbook must not hide the rest
                errors.append({"phase": "excel", "file": workbook_entry["path"], "error": str(exc)})

        photo_results = []
        photo_root = Path(manifest["photo_root"])
        if photo_root.is_dir():
            importer = StudentPhotoImporter(run.organization)
            photo_results.append(
                importer.import_directory(
                    photo_root,
                    overwrite=run.overwrite_photos,
                )
            )
            for archive_entry in manifest["photo_archives"]:
                archive_path = Path(manifest["source_root"]) / archive_entry["path"]
                try:
                    photo_results.append(
                        importer.import_zip(
                            archive_path,
                            overwrite=run.overwrite_photos,
                        )
                    )
                except ValueError as exc:
                    errors.append(
                        {"phase": "photos", "file": archive_entry["path"], "error": str(exc)}
                    )
        else:
            errors.append({"phase": "photos", "error": "مسیر Data/Photo پیدا نشد."})
        photo_summary = _merge_photo_results(photo_results)

        report_batches = []
        if run.generate_reports and imported_year_ids:
            try:
                report_batches = _queue_report_batches(run, imported_year_ids)
            except Exception as exc:
                errors.append({"phase": "reports", "error": str(exc)})

        summary = {
            "excel_files_seen": len(manifest["workbooks"]),
            "excel_jobs_created": sum(1 for job in child_jobs if job.source_kind == ImportJob.SourceKind.DATA_PATH),
            "excel_jobs_completed": sum(1 for job in child_jobs if job.status == ImportJob.Status.COMPLETED),
            "excel_jobs_failed": sum(1 for job in child_jobs if job.status == ImportJob.Status.FAILED),
            "academic_years": sorted(imported_year_ids),
            "photo_summary": photo_summary,
            "unsupported_excel": manifest["counts"]["unsupported_excel"],
            "unsupported_photos": manifest["counts"]["unsupported_photos"],
            "report_batches": report_batches,
        }
        run.result_summary = summary
        run.errors = errors[:1000]
        run.status = DataPathImport.Status.PARTIAL if errors or summary["excel_jobs_failed"] else DataPathImport.Status.COMPLETED
        run.finished_at = timezone.now()
        run.save(update_fields=["result_summary", "errors", "status", "finished_at", "updated_at"])
        return run
    except Exception as exc:
        run.status = DataPathImport.Status.FAILED
        run.errors = [*errors, {"phase": "scan", "error": str(exc)}][:1000]
        run.finished_at = timezone.now()
        run.save(update_fields=["manifest", "errors", "status", "finished_at", "updated_at"])
        return run
