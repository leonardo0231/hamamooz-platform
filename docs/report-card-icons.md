# Report-card icon selection

**Decision:** use a small, local inline-SVG vocabulary for the report card.
The icons are Lucide-inspired (24 × 24 viewBox, rounded stroke joins, and
`currentColor`) and are rendered locally so a PDF never depends on a remote
font or icon request. Text labels remain next to every icon; color and shape
are decorative, not the only way to communicate a result.

**Selected style:** calm educational marks in the existing navy, teal, gold,
rose, and neutral palette. UI icons use approximately 20–24 px; report-card
activity/award stickers use an approximately 42–48 px circular container on the
A3 sheet. Keep stroke width around 1.8–2.0 and preserve a clear area around the
path at print size.

## Approved semantic mapping

| Report meaning | Preferred icon | Fallback/implementation note |
| --- | --- | --- |
| School / report identity | `school`, `graduation-cap` | Use beside a text heading; the supplied school logo is a separate identity asset, not an icon substitute. |
| Academic learning | `graduation-cap`, `book-open` | Suitable for grade and learning panels. |
| Research / analysis | `microscope`, `brain-circuit` | Use for research, analytical thinking, or the radar section. |
| Sport / physical activity | `dumbbell` | Use for sports participation; keep the text label visible. |
| Art / creativity | `palette` | Use for arts and creative work. |
| Culture / reading | `book-open`, `library` | Use for book club and cultural participation. |
| Discipline / conduct | `shield-check` | Covers rules, responsibility, and positive discipline; do not use a warning icon for a positive achievement. |
| Attendance / punctuality | `calendar-check` | Use for attendance and follow-up status. |
| Competition / achievement | `trophy`, `medal` | Use for awards and placements. |
| Teamwork / participation | `users`, `handshake` | Use for group work and school participation. |
| Skills / wellbeing | `sparkles`, `heart-handshake` | Use only when the associated metric or text is present. |

The implementation must use a semantic name and an adjacent Persian label,
for example `نشان انضباط دانش‌آموز`. It must not use an emoji as the structural
icon, because emoji glyphs vary between operating systems and often disappear
or change shape in print/PDF.

## Local implementation contract

- Frontend icon paths live in `Frontend/src/components/icons.js` and are
  emitted as inline SVG with `fill="none"`, `stroke="currentColor"`, a
  `0 0 24 24` viewBox, rounded caps/joins, and `aria-hidden="true"` when the
  adjacent text supplies the accessible name.
- Report stickers use the same local vocabulary and a stable kind allow-list;
  unknown activity kinds fall back to a neutral activity/school mark rather
  than injecting arbitrary markup.
- Backend-rendered report cards must use a local SVG partial (or equivalent
  inline path data) and never fetch an icon from a CDN at PDF-render time.
- The school logo and student photo are content assets and must retain their
  own `alt`/accessibility text, sizing rules, and provenance. They are not
  replaced with a generated icon when missing.
- Every sticker keeps its text title and result. A screen reader, grayscale
  printer, or a low-resolution PDF must still convey the meaning without color.

## Sources and licensing

The candidate vocabulary was checked against the official Lucide icon catalog;
the following are the primary reference pages used for names and visual
semantics:

- [Graduation cap](https://lucide.dev/icons/graduation-cap)
- [Microscope](https://lucide.dev/icons/microscope)
- [Dumbbell](https://lucide.dev/icons/dumbbell)
- [Palette](https://lucide.dev/icons/palette)
- [Shield check](https://lucide.dev/icons/shield-check)
- [Calendar check](https://lucide.dev/icons/calendar-check)
- [Trophy](https://lucide.dev/icons/trophy)
- [Lucide license](https://lucide.dev/license)

Lucide is ISC-licensed. If an upstream Lucide path is copied verbatim into
the repository, keep the applicable license/attribution notice with the
vendored asset. If the path is redrawn or authored locally, retain the same
semantic naming and visual constraints without claiming it is an upstream
asset. [Google Material Symbols](https://developers.google.com/fonts/docs/material_symbols)
was also considered as a reference, but the printable report should not load
an external icon font or remote stylesheet.

## Cycle-4 acceptance checklist

- [x] Learning, research, sport, art, discipline, attendance, and achievement
      meanings have named icon candidates.
- [x] Icons are local vector paths and do not depend on emoji glyphs or a CDN.
- [x] Unknown/missing activity kinds have a neutral fallback.
- [x] Text labels remain visible beside stickers.
- [ ] VP confirms the selected symbols at A3 print scale and in grayscale.
- [ ] Real school/student assets are attached and checked separately from the
      decorative icon review.
