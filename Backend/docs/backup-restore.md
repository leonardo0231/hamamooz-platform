# Backup and Restore

The bundled backup service uses PostgreSQL-native `pg_dump` with checksum sidecars and retention.
Restore validates the checksum before `pg_restore`. CI creates a live dump, restores it into an
isolated PostgreSQL database and verifies migration history on every backend change.

The bundled private MinIO bucket has versioning enabled. Versioning is not an off-site backup:
production operators must replicate object storage and the database backup volume to encrypted,
access-isolated storage and periodically rehearse full application recovery.
