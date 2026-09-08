# Report-card change-request register

**Status:** active; approval is intentionally withheld until the school vice president (VP) signs off.

**Working branch:** `codex/mvp-report-card`

**Last curated:** cycle 7 · 2026-09-08

This register is the hand-off between the strict school-VP review agent, the
change-request curator, and the implementation agent. Every request stays in
the register until it has implementation evidence, a repeatable test or
visual check, and an explicit VP decision. A successful code check is not an
approval of missing school data or identity assets.

## Review loop

1. The VP reviews the rendered report and records a verdict and finding IDs.
2. The curator preserves the findings here and turns them into actionable
   requests, including any missing input that must come from the school.
3. The executor implements only saved requests and records the evidence.
4. The focused tests and the browser's fixed A3 print preview are checked.
5. The VP reviews again. The loop repeats until the VP records `APPROVED`.

The current state is **not approved**. The latest cycle is a follow-up pass,
not a replacement for the VP-01/VP-02 history.

## Data and asset intake gate

The following items are intentionally not guessed:

| Item | What is available | Required before production approval |
| --- | --- | --- |
| Student photos | `Data/Photo/` contains files named by national ID; the importer normalizes Persian/Arabic digits and supports a dry run. | A named school/organization, a known student national ID for visual verification, and authorization to import the matching portrait. There is no separate portrait attachment in this cycle. |
| School logo | The supplied school mark can be used by the demo renderer and the report has a school-logo → organization-logo fallback. | Associate the supplied mark with the exact `School` or `Organization` record. Do not infer the owner from a filename. |
| Grades | Report snapshots can render the scores already present in the approved database payload. | Identify the authoritative workbook or database scope: academic year, term, class, grade scale, and whether the workbook supersedes current rows. |
| Signatures and seal | The five required signature labels and bottom-row layout are present. | Names, signature images, and the school seal (if they must be printed). |
| Print profile | The implementation targets one fixed A3 landscape sheet. | Confirm the final physical printer margin/bleed requirement if it differs from the current 6 mm profile. |

When an analysis is not present in the snapshot, the report must show
`ثبت نشده` / “ثبت نشده” (not recorded), never a fabricated zero. Missing data
is also represented in the chart payload with an explicit availability flag.

## Browser-native report output

The report page and standalone sample now use the same self-hosted
Preact/HTM component tree (React-compatible component conventions) for the
visible report. Trend, radar, and bar charts are inline SVG, so the browser
print dialog receives the exact DOM reviewed on screen. The report toolbar
calls `window.print()` after fonts and images are ready, with an A3 landscape
print stylesheet that isolates the report sheet from the app shell. There are
no report PDF or ZIP download controls in the frontend.

This repository does not currently contain the `react`/`react-dom` packages or
a Playwright/Chromium worker. The implementation therefore does not claim a
literal React bundle or a server-side React PDF. The legacy Django archive
worker still contains a WeasyPrint path for backward compatibility, but it is
not used by the report preview/print flow. A final “all outputs are React”
approval remains blocked until that backend path is replaced by a deployed
React bundle plus Chromium renderer, or explicitly retired by the school.

### Cycle-4 source audit

The source folders and workbooks were inspected without importing or guessing
school-owned records:

- `Data/Photo/8/کدملی` contains 208 JPEGs; `besat.zip` is an exact duplicate of
  that set. One identifier has two different portraits, so both files are now
  blocked for review rather than selecting the first filename.
- `Data/Photo/9` contains 228 JPEGs and a separate RAR archive (RAR is not an
  accepted import format). All 436 JPEGs are valid RGB images under 2 MB; most
  are 159×213 and one is 945×1260.
- Grade 8 has 211 workbook students / 181 matching portraits / 30 missing / 26
  extra files. Grade 9 has 202 / 178 / 24 / 50. Grade 7 has no photo folder.
  These counts are an intake report, not an authorization to import.
- `801-802.xlsx` and `hamamooz_801.xlsx` overlap on 35 students; both must not
  be imported as authoritative. `902.xlsx` has no class value.
- The workbooks expose 46 metrics across the nine report domains: آموزشی،
  پرورشی، تربیتی، انضباطی، فرهنگی، پژوهشی، ورزشی، هنری، مهارت‌های فردی.
  Some `EDU_01` values are 0–20 and `EDU_02` contains decimal/negative and
  `ندارد` values, so no unapproved conversion to the official 0–5 scale is
  performed.
- Two workbooks reference a missing “فایل معاونین و کارشناسان” workbook for
  signer information. Names, signatures, and seals therefore remain input
  gates.

The safe dry-run command is:

```bash
python manage.py import_student_photos \
  --organization-id <UUID> \
  --directory Data/Photo \
  --dry-run
```

The command reports `duplicate_files` and never writes a portrait while a
student identifier has more than one candidate.

## Saved requests

Status vocabulary: **Implemented** means the code path exists; **Verification**
means the VP still needs to accept the rendered result; **Blocked** means a
school-owned input is required; **In review** means the VP loop is active;
**Deferred** means it is intentionally outside this approval pass.

| ID | Request | Cycle-4 status | Evidence / acceptance gate | Next action |
| --- | --- | --- | --- | --- |
| RC-01 | Put the information that exists in the Data section into the analytical report snapshot. | Implemented | `Backend/hamamooz/apps/reports/services.py`, `presentation.py`; focused reporting tests cover the snapshot contract. | VP verifies a populated snapshot against the source rows. |
| RC-02 | Distinguish an analysis that is absent from an analysis whose score is zero. | Implemented | Canonical domain rows carry `score`/`percent` plus availability; the template and frontend show `ثبت نشده`. | VP checks an intentionally incomplete fixture. |
| RC-03 | Keep one fixed, printable report format. | Implemented; visual verification | The browser report uses a single A3 landscape print profile and the report page no longer offers competing formats. | Compare browser print preview and the target school printer. |
| RC-04 | Display the student’s actual photo accurately, without stretching or silently substituting a different student. | Blocked by input | Existing photo data is keyed by national ID, but the target student and authorization are not supplied in this cycle. A visible fallback is used when no photo is recorded. | Provide the exact school/ID and approve the scoped import; VP then checks the crop. |
| RC-05 | Import the photos from `Data/Photo/` into student information. | Implemented; production run blocked | `StudentPhotoImporter` and `import_student_photos` support national-ID matching, strict duplicate blocking, and `--dry-run`. | Run only after the intake gate identifies the organization and authorized scope. |
| RC-06 | Put the supplied school logo in the output. | Verification; association blocked | School logo is preferred, with organization logo fallback; the demo accepts the supplied local mark. | Associate the uploaded mark with the exact school/organization record and re-render. |
| RC-07 | Increase text size and use Estedad or Vazirmatn. | Implemented; visual verification | Report templates and frontend print styles use `Estedad` for headings and `Vazirmatn` for body/data, with embedded/preloaded fonts. | VP checks legibility at 100% print size. |
| RC-08 | Make the spider/radar diagram large and readable and do not silently drop analyses. | Implemented; visual verification | Backend exposes all canonical domains; frontend no longer silently relies on a six-item slice for the report legend; the A3 radar has an enlarged view box. | VP checks labels and missing-state rendering at print scale. |
| RC-09 | Keep related sections, especially recommendations and follow-ups, together. | Implemented; visual verification | Recommendations are grouped into a single panel with audience-specific columns for parent/student, teachers/staff, and family support. | VP checks grouping and page flow. |
| RC-10 | Use educational, disciplinary, activity, and achievement stickers/icons like the supplied example. | Implemented; visual verification | Local inline SVG/Lucide-inspired icons are mapped by activity kind, including discipline; selection and sources are documented in `docs/report-card-icons.md`. | VP checks meaning, contrast, and print fidelity. |
| RC-11 | Place the signatures at the bottom in this exact order: Class Expert; Elementary Assistant; Educational Assistant; Executive Assistant; High School Principal. | Implemented; assets blocked | The fixed bottom signature row preserves all five labels and order. | Supply names/signatures/seal if the labels are to become signed output. |
| RC-12 | Include the authoritative grades and analysis values from the school’s information. | Blocked by input | The report renders approved snapshot values and explicit missing states; no unverified workbook was imported. | Provide workbook/scope or confirm the database snapshot as authoritative. |
| RC-13 | Preserve the student/academic identity details from the source of truth. | Implemented; fixture verification | Presentation reads student, enrollment, school, term, and analysis context from the report snapshot. | VP compares one known student record end to end. |
| RC-14 | Make the result printable as one fixed A3 landscape page. | Implemented; verification | Browser print CSS declares A3 landscape, 6 mm margins, shell isolation, and compact readable rows; native SVG charts share the screen DOM. | Verify one-page output in Chromium/Chrome with real photo/logo data. |
| RC-15 | Run the VP → curator → executor → VP loop until approval. | In review | VP-01 findings were saved; executor cycles record code/test evidence; this cycle adds the remaining asset/data gates. | Run the next strict VP review and append its verdict here. |
| RC-16 | Push each verified logical step to the remote gate with traceable evidence. | Implemented for frontend cycle | Frontend browser-print files were pushed sequentially after 21 tests, lint, build, and diff checks passed. | Push the documentation update and record the latest commit before VP review. |

## Review history

| Review | Verdict | Preserved findings and evidence |
| --- | --- | --- |
| VP-01 · initial strict review | **REJECTED** | VP-01..VP-12 identified: absent analyses collapsed to zero; radar/domain truncation; incomplete demo/PDF analysis data; raw numeric formatting; missing real photo/logo wiring; no end-to-end photo-folder import; unreadable typography and radar; separated recommendations; emoji/discipline gaps; inconsistent page sizes; and ignored/unsafe print CSS. These findings are retained above as RC-01–RC-14. |
| Curator after VP-01 | **SAVED** | Converted the VP findings into RC-01–RC-16, added the data/asset intake gate, and required evidence before approval. |
| Executor cycles 1–2 | **COMPLETED WITH FOLLOW-UPS** | Implemented the report data contract, canonical domains, availability states, logo fallback, photo importer, grouped recommendations, larger A3 composition, fonts, stickers, and signature labels. Focused backend tests and frontend syntax/lint checks passed in the working cycle; the actual school assets still require intake. |
| VP-02 · follow-up strict review | **NOT APPROVED / FOLLOW-UPS RETAINED** | The follow-up review remains part of the audit trail. It must not erase the open photo, logo association, authoritative grades, signature assets, and final print-verification gates. Append the exact VP-02 finding IDs and verdict when the review packet is returned. |
| Cycle 4 curator · 2026-09-08 | **SAVED; VP REVIEW PENDING** | Reconciled the register with the current working-tree implementation, made school-owned blockers explicit, and documented the selected local SVG icon set and official source/license references. |
| Cycle-7 browser-print executor · 2026-09-08 | **IMPLEMENTED; VP REVIEW PENDING** | Removed report PDF/ZIP controls from the frontend, replaced chart runtime rendering with inline SVG, added font/image readiness before `window.print()`, isolated the report sheet for A3 print, and added static contracts for the browser-native path. The backend WeasyPrint archive path remains an explicit infrastructure blocker, not an approved renderer. |

### VP-02 finding IDs preserved by the curator

The follow-up reviewer returned the following actionable findings; none is
silently closed by a passing unit test:

| Finding | Classification | Required disposition |
| --- | --- | --- |
| RC-04 / RC-05 | External input + safety | No authorized student portrait was available; duplicate candidates must be blocked and the target student/organization must be named. |
| RC-02 / RC-08 | Code/visual | The nine-domain radar/list must remain complete, readable, and explicit about missing values. |
| RC-10 | Code/visual | The browser report must render colored local SVG stickers, including the disciplinary shield, without emoji dependence; the legacy WeasyPrint archive path is not an accepted user-facing renderer. |
| RC-07 | Visual | Body and chart text must be legible at the fixed print scale. |
| RC-09 | Visual | Parent, teacher, and family-support recommendations must be one grouped section without duplicated fallback text. |
| RC-14 | Code/visual | Browser print preview must use one A3 landscape geometry and 6 mm print margin; a server PDF is not accepted until it executes the same report bundle in Chromium. |
| RC-06 / RC-12 / RC-11 | External input | Logo ownership, authoritative workbook/scale, signer names/images, and seal require school confirmation. |

### Cycle-4 implementation evidence

The executor applied the saved requests to the backend presentation contract,
photo importer, A3 template/renderer, frontend report, local SVG stickers, and
the test fixtures. The browser-print executor then made the frontend report
the canonical visible output and verified 21 frontend tests, lint, build, and
diff checks. The next VP packet must include a Chromium print-preview check,
focused backend tests, the frontend checks, and the remaining photo/logo/
grades/signatures inputs before any `APPROVED` verdict is recorded.

## Approval rule

The report is approved only when the VP records `APPROVED` for the same
rendered commit and the data/asset intake gate is either satisfied or explicitly
waived by the school. “Tests pass” alone cannot close RC-04, RC-06, RC-11, or
RC-12.
