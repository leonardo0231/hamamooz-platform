# Backup and Restore

The definitive backup/restore implementation and recorded restore drill belong to Slice 10. The target design uses PostgreSQL-native `pg_dump`/`pg_restore`, separate object-storage backup/versioning, encrypted off-host retention, checksums and a periodic restore into an isolated database.

No restore test has been claimed in Slice 0.
