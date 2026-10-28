# Operations

## Processes and health

Run the API and `python -m app.workers.run` as independently supervised processes. Worker ticks occur every 30 seconds; orphan-object sweeps occur roughly hourly, plus at worker startup. `--once` runs one tick and sweep for diagnostics or an external scheduler. Expired stories are denied on reads even if the worker is stopped.

The mail outbox is durable in PostgreSQL. Jobs stop retrying after five failed attempts. Investigate SMTP connectivity/credentials and the worker logs, then reset attempts for specifically reviewed failed jobs through an operator database session. The UI reports that mail is queued, not that external delivery succeeded.

`/health` reports API liveness. `/ready` tests SQL connectivity, migration metadata, and configured Redis. Readiness does not test sending SMTP mail or writing S3 objects; validate those separately. `/api/v1/admin/metrics` is role-restricted and contains in-process counters that reset on restart, including per-route status totals. Worker JSON logs include delivery/failure counts and removed assets per tick. Export logs/metrics to your monitoring system for durable dashboards and alerts; no external monitoring service is preconfigured.

## Backups

Enable managed PostgreSQL daily backups and point-in-time recovery. Set a retention period appropriate to the deployment (for example 30 days) and perform a restore drill before production. A local manual example, with PostgreSQL client tools installed:

```text
pg_dump --format=custom --file=luma-backup.dump --dbname=YOUR_POSTGRES_URL
pg_restore --no-owner --dbname=YOUR_NEW_EMPTY_DATABASE_URL luma-backup.dump
```

Use secure environment variables/credential files to avoid putting a real secret in shell history. Restore into a separate database; inspect it and run read-only smoke tests before changing application connections. Keep database backups encrypted and access restricted.

Enable S3 versioning and retention/lifecycle rules. A bucket delete operation may only create a delete marker in a versioned bucket; configure noncurrent-version expiry to implement your retention policy. Database-only backups do not contain media binaries.

## Retention and cleanup

- Session and reset/verification rows are removed after expiry. Revoked refresh rows remain until expiry for reuse detection.
- Stories expire after 24 hours, enforced on reads and eventually removed by the worker.
- Unreferenced media rows older than a day are removed. Generated object keys no longer in the database are removed after a 24-hour object-age grace period. A dedicated Luma bucket is required.
- Delivered mail bodies are replaced with a marker. Outbox records and local `.eml` files older than seven days are removed. Unsent jobs can contain email links until this retention limit; restrict DB/operator and local file access.
- Account deletion immediately removes access and cascades authored content/relationships. Storage and backups expire separately as above. Export provides account/content JSON plus media IDs, not a complete binary archive.
- Audit logs have no automated retention deletion in this release. Define an operator retention policy, avoid personal details in moderation notes, and purge according to your chosen policy using a reviewed maintenance job.

## Release maintenance

Run frontend lint/tests/build and backend tests/migration checks for every change. Run native PostgreSQL tests before release; the PGlite harness is a compatibility aid, not a concurrency/load substitute. Update dependencies through their lockfile tooling and scan dependencies and container images. Pin container digests and action commit SHAs in a controlled production release if your supply-chain policy requires immutable infrastructure references; the included development Compose images and CI actions use verified major-version channels.

Do not add production secrets to `.env.example`, a source archive, a Vercel `VITE_` variable, client logs or browser storage. Rotate secrets in the provider’s secret manager. Changing `SECRET_KEY` invalidates existing CSRF values; the API client retrieves a new one after a CSRF failure. Revoke sessions when an incident requires it.
