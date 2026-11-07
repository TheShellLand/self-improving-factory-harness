# Durable scheduling acceptance contract

Status: Phase 11 design only. The coordinator remains a library; this document
adds no daemon or automatic retries. Production scheduling depends on the
[Docker lifecycle](docker_rpc.md), [verified promotion](proposal_verification.md),
and [recovery](recovery.md) boundaries.

## Ownership and admission

Persist scheduler mode and ownership in the same authoritative vault used for
issue claims. Admission must atomically check that processing is enabled, the
caller owns scheduling, and no unresolved RUNNING session, PREPARED proposal, or
uncertain child termination blocks execution. Claim at most one issue and create
its session in that admission transaction. Separate polling reads cannot grant
permission to execute.

Use a host-generated owner identity and monotonically increasing ownership
version. Every claim and scheduler mutation must validate that version. Heartbeats
are diagnostic: expiration alone cannot prove an old worker or child has stopped.
A replacement scheduler may inspect state, but must not start model work until
host recovery proves prior execution stopped and resolves its durable blockers.
Fencing database writes alone does not stop an already running model process.

Issue selection must use a documented deterministic order, including a stable
secondary key for equal priority. Operator selection cannot bypass claim checks,
retry restrictions, or authorization. Recheck eligibility inside the transaction.
Keep the transaction short; do not hold a SQLite write transaction during model
execution, container cleanup, or Git operations.

## Pause, resume, and shutdown

Persist PAUSED or ENABLED as desired processing mode. A pause acknowledgement
means the mode was committed and no later admission may start while it remains
paused. A task admitted before that commit may finish; expose that distinction
in status. Pause does not cancel a running task or reconcile an interrupted one.
Serialize pause and admission through the same database boundary to resolve races.

Resume is an authorized state change, not a recovery action. It cannot clear
execution blockers or requeue failed issues. Retain mode across restart; a fresh
vault defaults to paused until explicitly enabled by the host operator.

Orderly shutdown stops local admission first and records the host's shutdown
intent. Permit the active attempt to finish within a configured grace period.
If cancellation becomes necessary, use bounded cleanup and preserve unresolved
RUNNING state until recovery verifies termination. Never mark success merely to
allow process exit. A later startup must inspect blockers before honoring enabled
mode. Process termination cannot implicitly erase a claim.

## Failure and audit behavior

Drive each admitted issue through Coordinator.run_once or an equivalent shared
claim/execution boundary; do not claim once in the scheduler and again in the
coordinator. Implementation must make that ownership explicit before integration.
Ordinary completed failures retain their attempt history. Retry only through the
existing explicit recovery rules; no polling cycle may silently requeue failures.

Persist operator identity, reason, previous/new mode, ownership version, and
transition time with each control mutation. Expose desired mode, active session,
owner, and blocking reason separately. A scheduler crash after claim but before
launch leaves a recoverable attempt, not permission for another execution.
Failures after Git commit retain the existing proposal reconciliation boundary.

Use bounded polling/backoff configured in config classes. Database unavailability
or audit write failure denies new admission. Avoid busy retry loops and keep
shutdown responsive during backoff. Inspect automonisaur before introducing
scheduler, locking, or retry helpers; connections remain owned by client classes.

## Acceptance evidence

Use multiple independent scheduler instances against one temporary vault to prove
that simultaneous admission produces only one model invocation. Cover pause versus
claim, resume with blockers, equal priorities, stale owner writes, expired heartbeat
with a still-running child, and restart after claim but before launch.

Inject crashes during execution, PREPARED intent, post-commit recording, and cleanup.
Verify retained attempts, no duplicate execution, and authorized reconciliation
before retry. Test shutdown within and beyond its grace period and restart while
paused. Verify every control transition has its audit record or neither commits.

A real-container demonstration must show sequential submitted issues, pause and
resume, orderly shutdown, interrupted-child recovery, and retained session and
commit evidence. Mocked tests alone cannot establish production termination or
complete the live scheduling milestone.
