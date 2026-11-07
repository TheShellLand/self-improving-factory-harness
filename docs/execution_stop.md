# Execution-stop verification acceptance contract

Status: Phase 14 design. Production stop verification remains unimplemented.
The [recovery service](recovery.md) accepts only boolean True from its synchronous
host verifier. This contract defines evidence required to justify that result.

## Durable identity and prevention of restart

Before launch, persist the session's host identity, scheduler ownership version,
parent execution identity, and intended child identity. After creation, bind the
actual container ID and daemon identity to that record. A PID alone is insufficient
because it can be reused; include a host boot identifier and process start identity
or equivalent supervisor-issued identity. Container names alone are insufficient
when names can be reused.

Fence further launches for the session before inspection. Hold that fence through
recovery's state transition so a worker cannot start between verification and claim
release. A pause flag or expired heartbeat does not establish this property. An
unreachable host or supervisor cannot supply proof that its execution has stopped.

## Verification procedure

Resolve all execution identities belonging to the session, including failed startup
attempts. Confirm the parent task cannot resume or launch more work, and inspect
each child on its recorded daemon. Confirm children are stopped or conclusively
absent and cannot be restarted by the host or their configured restart policy.
A stopped container with an active restart policy does not establish permanent stop.

Unknown launch outcomes require investigation using the persisted intended identity
and host labels. An empty child list is proof only when durable lifecycle records
establish that no child was created and no launch can still complete. Legacy
sessions without adequate identities remain blocked until an operator establishes
an auditable equivalent through the host integration.

Do not infer termination from Docker CLI exit, closed pipes, age, missing heartbeat,
FAILED application state, or a container missing from the wrong daemon. Permission
denied, timeout, daemon unavailability, ambiguous identity, and incomplete inventory
all mean uncertain termination. Return a refusal rather than truthy status text.

Keep inspection bounded with host configuration. If termination is needed, perform
it through the lifecycle client and then inspect again; sending a kill request is
not confirmation. Prefer separating explicit stop actions from the verifier's
read-only assessment so recovery does not unexpectedly terminate unrelated work.

## Evidence and integration

Retain session ID, ownership version, inspected identities, inspection timestamps,
parent/supervisor result, each child result, and the final decision and reason.
Do not store credentials or complete process environments. Evidence must be current
under the launch fence, not a cached success from an earlier inspection.

Connect this verifier to the existing RecoveryService and require operator
authorization separately. Reconcile PREPARED proposals before failing an interrupted
session, following the existing recovery workflow. Unknown execution must preserve
the durable admission blocker even when cleanup itself raises an exception.

## Acceptance evidence

Test PID reuse, host reboot identity changes, reused container names, wrong daemon,
late launch completion, restart policies, partial child inventory, permission errors,
timeouts, and loss of the launch fence. Verify none can produce successful recovery.
Test simultaneous recovery and launch attempts against the shared ownership state.

With real containers, demonstrate verified termination and authorized recovery,
plus daemon unavailability leaving the session blocked. Retain inspection evidence
and prove no subsequent claim overlaps the interrupted attempt. Inspect automonisaur
for reusable process and Docker facilities before implementation; bounded lifecycle
and client/config conventions continue to apply.
