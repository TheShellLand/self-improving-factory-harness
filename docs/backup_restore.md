# Backup and restore acceptance contract

This is the implementation contract for Phase 14. No backup or restore helper
is implemented or verified by this document. Persistent Docker volumes alone
are not backups. Follow [runtime setup](runtime_guide.md) and
[recovery operations](recovery.md) for existing behavior.

## Consistent capture

The future host-owned backup operation must stop admission of new work and
exclude all database and repository writers for the entire capture. This
includes API mutations, reflection, recovery, and Git promotion. Confirm parent
and child execution has stopped; elapsed time or a stale session is insufficient.
If exclusion or termination cannot be established, fail without publishing a
complete backup. Preserve RUNNING and PREPARED records without resolving them.

Capture SQLite through its backup API into a new destination, not by copying
only the main database file while journals may be active. Check database
integrity and foreign-key consistency on the captured database. Include all
issues, sessions, signals, observations, proposals, recovery evidence, and
strategy versions, preserving IDs and links.

Capture each repository referenced by proposal evidence, including recorded base
revisions and applied commit objects even when no current branch reaches them.
A default branch clone or an unchecked bundle of current refs is insufficient.
Record branch and HEAD state separately. Reject dirty repositories until their
state has been explicitly preserved and investigated; do not reset them.

## Backup manifest

Publish a versioned manifest only after all artifacts have been verified. Record:

- Backup ID, UTC capture time, application revision, and database schema version.
- Artifact relative paths, byte sizes, and SHA-256 digests.
- Original repository identities, branch/HEAD state, and required commit IDs.
- Counts of audit entities and unresolved sessions/proposals for restore checks.

Write into a new staging directory and publish the completed set atomically.
Failed captures must remain distinguishable from complete backups. Never replace
a previous valid backup on failure. Protect stored artifacts as sensitive audit
data; do not collect provider environment variables or credential files.

## Restore into an isolated destination

Restore must refuse an existing database or nonempty repository destination.
Validate manifest version, artifact paths and digests before consuming artifacts;
reject traversal, symlinks escaping the backup, missing files, and unknown formats.
Do not start the API, run migrations, schedule work, or contact model providers
as part of validation.

Open the restored database read-only for integrity and linkage checks. Verify
that every referenced Git revision exists and that recorded applied changes
match retained proposal evidence. Compare entity counts and strategy versions
with the manifest. Retain unresolved states exactly; restoring must not release
claims or authorize retries.

Repository evidence contains original paths. A restore to a different host must
retain those identities and provide an explicit audited mapping to restored
paths before enabling recovery. Do not silently rewrite evidence or point
recovery at the original live checkout. That mapping mechanism is pending.

## Required demonstration

Use disposable SQLite and Git fixtures containing an applied proposal, strategy
versions, a failed attempt, and unresolved RUNNING/PREPARED state. Capture and
restore into separate directories, then verify exact IDs, links, configuration
history, commit availability, and unresolved state. Include a referenced commit
that is unreachable from ordinary refs.

Negative tests must cover tampered and missing artifacts, invalid manifests,
unsafe paths, occupied destinations, failed capture, unavailable revisions,
concurrent writers, and uncertain execution termination. Each failure must leave
the source and any existing destination unchanged. Retain the verification report
and artifact identities before marking Phase 14 backup/restore tasks complete.
