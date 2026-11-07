# Strategy activation and rollback contract

Status: Phase 12 design. Activation enforcement and rollback remain unimplemented.
This contract extends the [evaluation contract](strategy_evaluation.md). Existing
reflection and hotloader APIs are not an adoption gate.

## Exact snapshots

Store complete baseline and candidate JSON snapshots with their hashes and version
identifiers. The candidate is evaluated without changing active configuration.
Only a complete, verified IMPROVEMENT comparison can make it eligible for activation;
NO_CHANGE, REGRESSION, and INCONCLUSIVE leave the active baseline unchanged.
Eligibility is not authorization: the host must also validate execution provenance,
policy, and that the retained evidence belongs to these exact snapshots.

A rollback restores the entire prior accepted snapshot. Appending its keys through
the current top-level merge semantics is insufficient: keys introduced by the
candidate would survive. Implement explicit snapshot replacement semantics and
preserve them during restart replay. Do not encode deletion using null, because
null is a valid JSON configuration value. Preserve exact JSON value types.

## Atomic activation

A host-owned activation service must use a database transaction to compare the
active version and hash with the evaluated baseline and then append the activation
record and advance the active pointer. Check both version and hash so an intervening
change followed by restoration cannot make stale evidence appear current.
Concurrent activation attempts cannot both succeed against one baseline.

Record the candidate snapshot, previous active version, evaluation identifier and
hash, policy version, host decision, and activation identity. Never accept a model's
success flag or caller-supplied score as authorization. A missing artifact, changed
policy, stale baseline, or failed evidence verification rejects activation without
changing the active pointer. Keep rejected attempts and reasons in the audit history.

Prevent time-of-check/time-of-use replacement of verified artifacts: bind activation
to immutable retained evidence or copy verified evidence into host-owned storage
before the transaction. File hashes alone do not authenticate a model run.

## Application and recovery

New task claims capture an accepted configuration version and use its exact snapshot
for the whole attempt. Activation must not silently alter an in-flight attempt.
The loader acknowledges which version it applied; startup reconstructs the active
snapshot from committed records. It must not replay rejected candidates as updates.
If a committed activation cannot be loaded, block new execution and retain a visible
failure until restoration or repair completes.

A restoration transaction compares the active version with the version being rolled
back, appends a new restoration record containing the prior accepted snapshot, and
advances the pointer. Keep history append-only; never delete the failed activation
or move a version counter backward. If another activation has intervened, reject
the stale restoration rather than overwriting newer accepted configuration.

Use stable operation identifiers so retries after a lost response return the
recorded outcome without creating duplicate activations or restorations. A crash
before commit leaves the old pointer; a crash after commit is resolved from durable
records. External evidence storage and SQLite are not one transaction: incomplete
staging cannot authorize activation and should remain inspectable.

## Acceptance evidence

Use temporary vaults to demonstrate:

- Rejected or incomplete evaluations leave the baseline active.
- A verified eligible candidate becomes active once with linked evidence.
- Concurrent activation, stale baseline versions, and altered evidence are rejected.
- Restoration removes candidate-only keys and preserves nested objects and nulls.
- Restart replay produces the exact restored snapshot and hash.
- Duplicate operation requests and crashes around commit do not duplicate changes.
- Loader failure blocks admission; an in-flight task retains its captured version.
- Stale restoration cannot replace a newer activation.

Inspect automonisaur for reusable transaction and configuration helpers before
implementation. Keep settings in config classes and connections in client classes.
A live demonstration must link a real comparison, activation, failed acceptance
condition where applicable, restoration decision, and subsequent loaded snapshot.
Do not mark implementation or live rollback complete based on this contract.
