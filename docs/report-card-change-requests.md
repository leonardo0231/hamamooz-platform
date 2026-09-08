# Report-card change-request register

**Status:** active; approval is intentionally withheld until the school vice president (VP) signs off.

**Working branch:** `codex/mvp-report-card`

**Last curated:** cycle 9 · 2026-09-08

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

The report page and standalone sample now use the same local React 19/ReactDOM
component tree. Existing HTM templates are bound through
`Frontend/src/core/view.js`, which normalizes the legacy attribute spelling at
one boundary so the reviewed report DOM and print CSS remain stable. Trend,
radar, and bar charts are inline SVG, so the browser print dialog receives the
exact DOM reviewed on screen. The report toolbar calls `window.print()` after
fonts and images are ready, with an A3 landscape print stylesheet that isolates
the report sheet from the app shell. There are no report PDF or ZIP download
controls in the frontend. Vite builds both the application and standalone
report entries into a local production bundle.

The selected target for C7-01 is literal React/ReactDOM in the browser;
Next.js is not required for this report surface. The standalone Vite bundle is
the canonical report entry. The production `render_report_pdf` path injects an
authorized snapshot into that React entry, waits for `__REPORT_READY__`, and
prints A3 landscape through Playwright/Chromium. Missing Playwright, Chromium,
or the configured frontend URL raises an explicit `ReportRendererUnavailable`;
there is no production WeasyPrint or legacy-engine fallback. The API preview
also returns a React hand-off contract (renderer, A3 layout, frontend/print
URL, and snapshot); its compatibility `html` field is a non-rendering marker,
not Django report markup.

### Cycle-8 React/Vite migration evidence

The following commits were verified on the remote branch as the sequential
React/Vite migration and report-adapter implementation:

| Commit | Evidence |
| --- | --- |
| [`9b59305e`](https://github.com/leonardo0231/hamamooz-platform/commit/9b59305e83da330840f16199c91a6c4b6fc4960f) | React 19 and Vite dependencies |
| [`9316b66c`](https://github.com/leonardo0231/hamamooz-platform/commit/9316b66c707499921df8b8d3947b6fe193738cb1) | Locked React/Vite dependency tree |
| [`12dff617`](https://github.com/leonardo0231/hamamooz-platform/commit/12dff617cef20db7bf647ed59675fbab8eeb6bf2) | Vite app and printable-report entries |
| [`05f58cda`](https://github.com/leonardo0231/hamamooz-platform/commit/05f58cdaf2095bc291270b09a5d61a084a73b498) | React report Vite bundle |
| [`3ee1d2de`](https://github.com/leonardo0231/hamamooz-platform/commit/3ee1d2de0f8cf0cf333739b76dedf2e142082c4e) | Vite development proxy alignment |
| [`a06184d6`](https://github.com/leonardo0231/hamamooz-platform/commit/a06184d66322cca165a7b4411c843b3158b128b3) | HTM templates rendered through ReactDOM |
| [`22b1ea7b`](https://github.com/leonardo0231/hamamooz-platform/commit/22b1ea7b705814b0aadaaf0d836b52a3ffce3354) | Multipart comprehensive import repair |
| [`65bb72a0`](https://github.com/leonardo0231/hamamooz-platform/commit/65bb72a06628ee642184a52421d984d44bdfbe1a) | React report build documentation |
| [`6ab8fd4c`](https://github.com/leonardo0231/hamamooz-platform/commit/6ab8fd4c523662cec75f4d2163bf84ebfdc11940) | Vite config copied into the container build |
| [`967824e7`](https://github.com/leonardo0231/hamamooz-platform/commit/967824e7bf5e216355f321dd498246142d869784) | ReactDOM report-adapter contract test; remote head at review time |

The executor reported **23 frontend tests, lint, and Vite build** passing
locally. This is local evidence only and must not be represented as a green
GitHub Actions run while backend CI is unverified or red.

### Cycle-8 snapshot and CI follow-up evidence

The next remote sequence added secure snapshot injection and repaired the
generated migration that had been missing from the earlier backend run:

| Commit | Evidence |
| --- | --- |
| [`6cb7b81`](https://github.com/leonardo0231/hamamooz-platform/commit/6cb7b8194d73dbdbec47145e5675957788edae18) | React/Vite report architecture documentation |
| [`ee55f36`](https://github.com/leonardo0231/hamamooz-platform/commit/ee55f3630f98d18553e11cdd1eaf02938f52d317) | Adds the generated evaluations migration required by backend validation |
| [`fbd09fe`](https://github.com/leonardo0231/hamamooz-platform/commit/fbd09fe0680b7af969ea01c2038c1b0b7c29bf35) | Allows an already-authorized report snapshot to be injected into the React print entry without putting student data in the query string |
| [`271880cc`](https://github.com/leonardo0231/hamamooz-platform/commit/271880cc810c3e7257d075331c98df9b9833496e) | Adds the injected-snapshot print-entry contract test; current remote head at verification time |

For the earlier head [`967824e7`](https://github.com/leonardo0231/hamamooz-platform/commit/967824e7bf5e216355f321dd498246142d869784), [Frontend CI run 34236414092](https://github.com/leonardo0231/hamamooz-platform/actions/runs/34236414092) passed, while [Backend CI run 34236414165](https://github.com/leonardo0231/hamamooz-platform/actions/runs/34236414165) failed because the generated migration was not present yet; `ee55f36` was committed afterward to add it. The current head `271880cc` has no associated workflow run or status in the present GitHub API check, so `R7-CI-01` remains unverified.

### Cycle-8 remaining VP blockers

| Area | Current blocker | Closure required |
| --- | --- | --- |
| React/Next target | React 19/ReactDOM + Vite is now implemented, but this is not a Next.js app. | The VP must accept React/Vite as the selected target or require a literal Next.js migration; do not claim both. |
| Server renderer | `render_report_pdf` now delegates to the Chromium boundary and has no legacy-engine fallback. | Keep the Chromium dependency/runtime pinned and attach a real A3 browser artifact before approval. |
| Chromium/A3 evidence | A `ChromiumReportRenderer` helper exists, but Playwright/Chromium is not wired or provisioned for production and no real Chrome A3 print artifact is available. | Provision the runtime and attach a deterministic one-page A3 Chrome print/PDF check covering radar/readability. |
| School-owned inputs | The real target photo, logo association, authoritative grades/workbook, signer names/signatures, and seal remain missing or unapproved. | Provide and authorize the scoped assets/data; preserve duplicate and missing-photo safety gates. |
| Backend CI | Frontend CI run 34236414092 passed; backend CI run 34236414165 failed before `ee55f36` added the generated migration. The current head `271880cc` has no associated workflow run/status in the present API check; Docker validation is insufficient. | Produce a green backend Ruff/integration workflow run for the post-migration head or record a VP-approved exception with the failure classification. |

### Cycle-4 source audit

The source folders and workbooks were inspected without importing or guessing
school-owned records:

- `Data/Photo/8/کدملی` contains 208 JPEGs; `besat.zip` is an exact duplicate of
  that set. Duplicate identifiers and missing matches are recorded as review
  states; one identifier has two different portraits, so both files are now
  blocked rather than selecting the first filename.
- `Data/Photo/9` contains 228 JPEGs and a separate RAR archive (RAR is not an
  accepted import format). All 436 JPEGs are valid RGB images under 2 MB; most
  are 159×213 and one is 945×1260. The counts are an audit summary only and do
  not expose or repeat any student identifier.
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
- Two workbooks contain an external link to the missing “فایل معاونین و
  کارشناسان” workbook for signer information. Names, signatures, and seals
  therefore remain input gates; the external link is not treated as a source
  until the school supplies and approves the referenced file.

The safe dry-run command is:

```bash
python manage.py import_student_photos \
  --organization-id <UUID> \
  --directory Data/Photo \
  --dry-run
```

The command reports `duplicate_files` and never writes a portrait while a
student identifier has more than one candidate.

## VP cycle-7 findings

The strict VP cycle-7 findings are saved as six separate requests. They are
deliberately split between product architecture, renderer infrastructure,
rendered-output verification, and school-owned inputs so that a code change
cannot be used to close an input blocker.

| Finding | Category | Saved status | Exact disposition / next action |
| --- | --- | --- | --- |
| C7-01 | Literal React/Next migration | **Implemented — React target; VP verification pending** | `Frontend/src/core/view.js` now creates React elements and ReactDOM roots while retaining the HTM template boundary; `Frontend/package.json` pins React/ReactDOM and Vite; `Frontend/vite.config.mjs` builds the app and standalone report entries. This closes the React choice for C7-01, but does not claim a Next.js migration or VP approval. |
| C7-02 | Legacy PDF renderer retirement | **Implemented — VP verification pending** | `render_report_pdf` delegates to `rendering.render_production_report_pdf`; the active dependency manifests contain pinned Playwright and no WeasyPrint package. The service has no legacy-engine fallback. | Verify the same approved snapshot through the deployed Chromium runtime and retain the explicit unavailable error when the browser bundle is absent. |
| C7-03 | Chromium report infrastructure | **Implemented — real artifact pending** | The backend image declares pinned Playwright, provisions `playwright install --with-deps chromium`, and the renderer covers local asset base URLs, font readiness, timeout, and explicit startup errors. The focused boundary tests pass. | Run the image and attach a deterministic one-page A3 Chromium PDF/print check covering radar/readability; this step does not claim server-side React bundle rendering. |
| C7-04 | Visual A3/radar verification | **Implemented — real Chrome evidence pending** | The frontend declares a single A3 landscape print profile and the charts are native SVG, but no real Chrome A3 print artifact has been accepted. The VP must inspect at 100%: one page, no clipping, readable typography, all nine domain labels, explicit missing states, and a sufficiently large radar. |
| C7-05 | School-owned photo/logo inputs | **Blocked — school input** | The photo audit has 208 JPEGs for grade 8 and 228 for grade 9, with duplicate IDs and missing matches; no target student/authorization was supplied. The uploaded logo is not associated with a confirmed `School`/`Organization` record. Provide the scoped school, target student ID, import authorization, duplicate resolution, and logo ownership. |
| C7-06 | School-owned Excel/grades/signature inputs | **Blocked — school input** | The workbooks expose 46 indicators across nine domains, but `EDU_01` mixes 0–20 values and `EDU_02` includes negative/decimal/`ندارد` values. Overlapping workbooks, a workbook without class data, and an external link to the missing معاونین/کارشناسان file leave authority and scale unresolved. Provide the authoritative workbook, year/term/class/scale, and signer names/signatures/seal; do not import or convert unapproved values. |

These six findings are additive to RC-01–RC-16 and do not rewrite the prior
VP-01 or VP-02 history.

## Saved requests

Status vocabulary: **Implemented** means the code path exists; **Verification**
means the VP still needs to accept the rendered result; **Blocked** means a
school-owned input is required; **In review** means the VP loop is active;
**Deferred** means it is intentionally outside this approval pass.

| ID | Request | Current status | Evidence / acceptance gate | Next action |
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
| RC-16 | Push each verified logical step to the remote gate with traceable evidence. | **Implemented for frontend; docs/backend hand-off pending** | The frontend commits were verified on the remote branch in sequence: [`df51d107`](https://github.com/leonardo0231/hamamooz-platform/commit/df51d1073bfd6b4a1ba4874cf21536002578d696) for `Frontend/src/styles/reports.css`, followed by [`63912cf`](https://github.com/leonardo0231/hamamooz-platform/commit/63912cf015a1016928899de8acd081cbc484a299) for `Frontend/src/pages/reports.js`. The commits are not unpushed; this status covers the frontend evidence only. | Parent agent records the remaining documentation/backend commits sequentially, then sends the same remote commit set to the VP. |
| R7-CI-01 | Make backend Ruff and integration CI green; Docker validation alone is not sufficient evidence. | **Open — CI status unverified / previous run red** | The cycle-7 VP re-review at remote head `b2f4c6df` found that backend Ruff/integration checks were not green; only Docker validation was evidenced. The cycle-8 local frontend evidence does not close backend CI. | Run the backend Ruff and integration suites in CI, fix or explicitly classify every failure, and attach a green run to the next VP packet. |

## Review history

| Review | Verdict | Preserved findings and evidence |
| --- | --- | --- |
| VP-01 · initial strict review | **REJECTED** | VP-01..VP-12 identified: absent analyses collapsed to zero; radar/domain truncation; incomplete demo/PDF analysis data; raw numeric formatting; missing real photo/logo wiring; no end-to-end photo-folder import; unreadable typography and radar; separated recommendations; emoji/discipline gaps; inconsistent page sizes; and ignored/unsafe print CSS. These findings are retained above as RC-01–RC-14. |
| Curator after VP-01 | **SAVED** | Converted the VP findings into RC-01–RC-16, added the data/asset intake gate, and required evidence before approval. |
| Executor cycles 1–2 | **COMPLETED WITH FOLLOW-UPS** | Implemented the report data contract, canonical domains, availability states, logo fallback, photo importer, grouped recommendations, larger A3 composition, fonts, stickers, and signature labels. Focused backend tests and frontend syntax/lint checks passed in the working cycle; the actual school assets still require intake. |
| VP-02 · follow-up strict review | **NOT APPROVED / FOLLOW-UPS RETAINED** | The follow-up review remains part of the audit trail. It must not erase the open photo, logo association, authoritative grades, signature assets, and final print-verification gates. Append the exact VP-02 finding IDs and verdict when the review packet is returned. |
| Cycle 4 curator · 2026-09-08 | **SAVED; VP REVIEW PENDING** | Reconciled the register with the current working-tree implementation, made school-owned blockers explicit, and documented the selected local SVG icon set and official source/license references. |
| Cycle-7 browser-print executor · 2026-09-08 | **IMPLEMENTED; VP REVIEW PENDING** | Removed report PDF/ZIP controls from the frontend, replaced chart runtime rendering with inline SVG, added font/image readiness before `window.print()`, isolated the report sheet for A3 print, and added static contracts for the browser-native path. The initial frontend sequence is verified by [`df51d107`](https://github.com/leonardo0231/hamamooz-platform/commit/df51d1073bfd6b4a1ba4874cf21536002578d696) → [`63912cf`](https://github.com/leonardo0231/hamamooz-platform/commit/63912cf015a1016928899de8acd081cbc484a299); the follow-up sequence synchronizes the dependency metadata, native SVG charts, enlarged print layout, and tests via [`604b18c`](https://github.com/leonardo0231/hamamooz-platform/commit/604b18c6a510b8b307e31ba3c4c03896f5661270), [`4f81b30`](https://github.com/leonardo0231/hamamooz-platform/commit/4f81b30ff7d6d170b5645f5a7ef9d5c1011ec160), [`5d07de1`](https://github.com/leonardo0231/hamamooz-platform/commit/5d07de1facf356ed71cf6c7862e3580169ef063b), [`831479f`](https://github.com/leonardo0231/hamamooz-platform/commit/831479f6b342271fd1506e0fe7eb143c5a325c64), and [`873083e`](https://github.com/leonardo0231/hamamooz-platform/commit/873083e8e8197711bad618a264ee6831964dd797). The backend WeasyPrint archive path remains the C7-02 infrastructure blocker, not an approved renderer. |
| Cycle-7 strict VP review · 2026-09-08 | **REJECTED / FOLLOW-UPS SAVED** | C7-01 through C7-06 are recorded above. The VP did not approve the report while literal React/Next migration, renderer infrastructure, A3/radar visual evidence, and school-owned identity/grade/signature inputs remain unresolved. |
| Cycle-7 VP re-review · 2026-09-08 · remote head `b2f4c6df` | **CONDITIONAL — INPUTS/INFRASTRUCTURE REQUIRED** | Passed: ECharts was removed from the report path; charts are inline SVG; the fixed A3 layout, radar, readiness, photo/logo fallbacks, grouped recommendations, stickers, and bottom signatures are present; 21 frontend tests, lint, and build passed. Remaining blockers are C7-01–C7-06. New finding R7-CI-01 records that backend Ruff/integration CI is not green and only Docker validation is evidenced. |
| Cycle-7 current-head curator verification · 2026-09-08 · [`b17dd4c`](https://github.com/leonardo0231/hamamooz-platform/commit/b17dd4c37f13f23d3863042d0ff2ff2d39cbdce8) | **CONDITIONAL — INPUTS/INFRASTRUCTURE REQUIRED (NOT APPROVED)** | Head `b17dd4c` is the CI-trigger attempt (`chore(ci): trigger backend validation after legacy import cleanup`). GitHub exposes `backend-ci.yml` and `frontend-ci.yml`, but the head has no associated workflow run and no combined status checks yet (`workflow_runs=[]`, `statuses=[]`) at verification time. Latest frontend evidence remains the remote sequential push `df51d107` → `63912cf`; latest backend evidence includes the corrected `ChromiumReportRenderer.page.pdf(format="A3")` call, while the report service still retains the legacy WeasyPrint path. C7-01–C7-06 remain open, and R7-CI-01 is not closed by the trigger commit. |
| Import smoke-timeout follow-up · 2026-09-08 · [`b86765a`](https://github.com/leonardo0231/hamamooz-platform/commit/b86765a27df49408da02bfd4c5a822f597b466ab) | **DIAGNOSED; CI UNVERIFIED** | Root cause identified: the import create path now queues `process_import_job_task.delay(...)` inside `transaction.on_commit`, so the task is not dispatched before the upload transaction is durable. Local Ruff/compile checks were recorded for the change. GitHub API commits currently produce no associated workflow runs/statuses in this verification, so `R7-CI-01` remains open and Docker-only validation is not sufficient to close it. |

| Cycle-7 C7-01 React/Vite executor · 2026-09-08 | **IMPLEMENTED; VP REVIEW PENDING** | Replaced the frontend renderer boundary with React 19/ReactDOM, retained HTM templates through the compatibility adapter, added a pinned Vite multi-page build for the dashboard and standalone A3 report, and flushed the initial React commit before print-readiness inspection. Native SVG charts and the existing A3 browser print DOM remain the canonical report path. Direct frontend evidence: 23 Node tests, source lint, Vite production build, package-lock consistency, and `git diff --check` all passed. The remote commit sequence is recorded below; it is not an unpushed local change. |
| Cycle-8 strict VP review · 2026-09-08 · remote head [`967824e7`](https://github.com/leonardo0231/hamamooz-platform/commit/967824e7bf5e216355f321dd498246142d869784) | **CONDITIONAL — INPUTS/INFRASTRUCTURE REQUIRED (NOT APPROVED)** | Passed: React 19/ReactDOM + Vite migration, inline SVG report charts, fixed A3 layout, radar/readiness, fallbacks, grouped recommendations, stickers, signatures, and local evidence of 23 frontend tests, lint, and Vite build. Remaining blockers: server `render_report_pdf` still uses WeasyPrint; Playwright/Chromium is not wired/provisioned; no real Chrome A3 artifact; school-owned photo/logo/grades/signers are missing; and backend CI is unverified with the previous run red. C7-01 remains a Next.js decision/waiver if Next is mandatory; C7-02–C7-06 and R7-CI-01 remain open. |
| Cycle-8 snapshot/CI follow-up · 2026-09-08 · remote head [`271880cc`](https://github.com/leonardo0231/hamamooz-platform/commit/271880cc810c3e7257d075331c98df9b9833496e) | **CONDITIONAL — INPUTS/INFRASTRUCTURE REQUIRED (NOT APPROVED)** | Secure snapshot injection (`fbd09fe`) and its contract test (`271880cc`) are present; the generated evaluations migration was added in `ee55f36` after the earlier backend failure. Frontend CI run 34236414092 passed; backend CI run 34236414165 failed before that migration. The current head has no associated workflow run/status in the present API check. WeasyPrint replacement, Chromium provisioning and real Chrome A3 evidence, school-owned photo/logo/grades/signers, and a green post-migration backend CI run remain required. |
| Cycle-8 C7-02/C7-03 renderer-boundary executor · 2026-09-08 · commits [`4441057d`](https://github.com/leonardo0231/hamamooz-platform/commit/4441057d828191a88cd553f60ec642f70f3c46fa) → [`da81f812`](https://github.com/leonardo0231/hamamooz-platform/commit/da81f8129890d83d5c73ede07b1398e4776a947f) → [`2c7700d7`](https://github.com/leonardo0231/hamamooz-platform/commit/2c7700d7ea3a87d2207a4673123b300d2a0df3a3) → [`d1932890`](https://github.com/leonardo0231/hamamooz-platform/commit/d19328901664154c0142a651f8e9852b2f39ee82) → [`55c255c1`](https://github.com/leonardo0231/hamamooz-platform/commit/55c255c1e1251c81e068a7bba68c6697a5a7bc4c) | **PARTIAL IMPLEMENTATION — VP REVIEW PENDING** | `render_report_pdf` now selects the Chromium renderer through `rendering.render_production_report_pdf`; missing Playwright/Chromium raises `ReportRendererUnavailable`, with no WeasyPrint fallback. The renderer preserves A3 landscape PDF options, injects the application base URL for local fonts/assets, waits for document fonts, and has three focused boundary tests passing. This is Chromium over Django snapshot HTML, not server-side React; the Playwright dependency/browser bundle, real Chrome A3 artifact, school-owned assets/data, and backend CI remain open. |

| Cycle-9 React/Chromium production executor · 2026-09-08 · commits [`4a003721`](https://github.com/leonardo0231/hamamooz-platform/commit/4a00372131908dbf0c75dec27488f044da1de6cd) → [`42ba0290`](https://github.com/leonardo0231/hamamooz-platform/commit/42ba0290cdf6b2bda3674970dbf0ce0d4fd28e11) → [`fc45fbe8`](https://github.com/leonardo0231/hamamooz-platform/commit/fc45fbe885107c76457f3b2ea2058864edcbdd8a) | **IMPLEMENTED; CI/A3/input verification pending** | Production PDF now loads the built React report entry, injects the frozen snapshot before module execution, waits for readiness/fonts/images, and prints A3 landscape with Chromium. Playwright is pinned and provisioned in Docker/CI; no WeasyPrint fallback exists. |
| Cycle-9 React-only preview contract · 2026-09-08 · commits [`67afb78a`](https://github.com/leonardo0231/hamamooz-platform/commit/67afb78a0b3663cb112af67c3e45d5fe4e225e11) → [`692eed9b`](https://github.com/leonardo0231/hamamooz-platform/commit/692eed9b48f65adf648ac655e7c2630f98dce0f6) | **IMPLEMENTED; CI pending** | `/reports/preview/` no longer calls the Django report template. It returns the React renderer contract and the authorized snapshot; the legacy `html` key is retained only as a non-rendering compatibility marker. |

### VP-02 exact blockers preserved by the curator

The following concrete blockers remain from the VP-02 follow-up. None is
silently closed by a passing unit test, and no personal identifier is written
in this register:

| Blocker | Classification | Required disposition |
| --- | --- | --- |
| VP02-PHOTO | External input + safety | No authorized target student portrait was available. Duplicate candidates and missing matches in the grade-8/grade-9 audit must stay blocked; the organization/school and target student must be named before a scoped import. |
| VP02-LOGO | External input | The supplied school logo has no confirmed `School`/`Organization` association. Confirm ownership and re-render the same student report. |
| VP02-GRADES | External input + data integrity | Authoritative workbook, academic year, term, class, and scale are unresolved; overlapping files and the missing class value must be resolved before import. Preserve raw values until the school approves normalization. |
| VP02-SIGNATURES | External input | The referenced “فایل معاونین و کارشناسان” workbook is missing. Signer names, signature images, and seal remain required inputs. |
| VP02-RADAR | Code/visual | The nine-domain radar/list must remain complete, readable, and explicit about missing values. The VP must see a real A3 browser print preview. |
| VP02-RENDERER | Code/infrastructure | The browser report remains the user-facing path with local SVG stickers and no emoji dependence; the server PDF boundary is now Chromium-only and fails explicitly when its runtime is missing, but real Chromium parity/print evidence is still required before approval. |

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
