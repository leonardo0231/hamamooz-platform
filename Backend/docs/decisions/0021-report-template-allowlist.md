# ADR 0021: Report Templates Use an Allowlisted Block Model

- Status: accepted
- Date: 2026-08-10

## Context

Administrator-authored Jinja/Python would introduce template injection and an unmaintainable report runtime.

## Decision

Represent a report template as an ordered list of allowlisted blocks plus bounded title/logo/signature/footer/style configuration. Do not execute arbitrary template code supplied by users.

## Consequences

- New blocks are code-reviewed capabilities.
- Report configuration is validated schema data, not executable content.
- PDF rendering can remain WeasyPrint without a custom templating language.

## References

- `Backend/docs/21-REPORTING_PLATFORM_FA.md`
- `docs/product/FULL_PRODUCT_ROADMAP_FA.md`
