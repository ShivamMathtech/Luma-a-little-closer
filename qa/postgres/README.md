# Optional PostgreSQL compatibility harness

Run from the project root after installing backend dependencies:

```text
npm --prefix qa/postgres ci
python qa/postgres/run.py
```

This starts a temporary, loopback-only PGlite database on port 55432, applies the real Alembic migrations, checks schema drift, runs the entire API suite, and exercises downgrade/upgrade. It stops the database and discards its isolated temporary directory afterward. Keep port 55432 free.

PGlite runs PostgreSQL compiled to WebAssembly. Its socket multiplexer is not the same as a native multi-connection PostgreSQL server. Tests use autocommit for the test fixture's separate inspection connection, while application transactions are unchanged. This avoids an unsupported overlap of inspection and application transactions in the single-backend harness. Native PostgreSQL CI and real concurrency/load tests remain necessary for production confidence.

The main application does not depend on or use this package. Production must use PostgreSQL.
