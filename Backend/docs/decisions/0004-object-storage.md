# ADR 0004: S3-Compatible Object Storage

- Status: accepted
- Decision: use Django storage abstraction with private S3-compatible storage in deployed environments and filesystem storage for local development.
- Consequence: report/download services must issue short-lived authorized links and audit downloads; bucket public access remains disabled.
