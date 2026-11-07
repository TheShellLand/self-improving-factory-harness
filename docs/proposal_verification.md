# Proposal verification and promotion acceptance contract

This contract specifies Phase 10. Verification and enforced promotion are not
implemented yet. Follow the [runtime guide](runtime_guide.md) for setup and the
[Docker lifecycle contract](docker_rpc.md) for bounded execution and recovery.

## Host-owned inputs

The host captures the repository identity, target branch, full base commit ID,
issue ID, session ID, commit message, and exact proposed file replacements before
verification. Reuse gatekeeper path validation; reject traversal, symlinks, and
unsupported paths before materializing files. Treat agent summaries and success
flags as observations, never as check results.

The host selects check commands and their policy version. Proposed files cannot
change the commands, required checks, timeouts, or acceptance rules for their own
verification. Configuration classes own limits; client classes own Git and Docker
connections. Inspect automonisaur before implementing new helpers.

## Isolated execution

Create a disposable checkout at the recorded base revision and apply exactly the
captured replacements. Preserve the parent checkout and index. Never execute
proposed code on the host or give a check container the Docker socket, host Git
credentials, or a writable parent checkout. Use a separate repository copy when
Git worktree metadata would expose writable parent repository internals.

Run checks as an unprivileged user with host-selected resource, output, execution,
and cleanup limits. Network access is disabled unless the host policy explicitly
requires it. Dependency acquisition must be separately controlled and recorded.
A missing check, launch failure, nonzero exit, timeout, output overflow, or missing
termination proof cannot yield acceptance. Uncertain termination blocks further
execution durably under the Docker lifecycle contract.

## Evidence and acceptance

Persist immutable verification evidence linked to the issue and session:

- Repository, branch, base revision, proposal message, and replacement paths.
- Cryptographic hashes of each replacement's exact bytes and a canonical manifest
  binding the complete path set, contents, message, and base revision.
- Check policy version, exact argv, relevant nonsecret settings, resolved image ID,
  and tool/dependency versions needed to interpret the run.
- Each required check's start/end times, exit status, bounded output and truncation
  markers, plus timeout, cancellation, and cleanup outcomes.
- The aggregate decision and its reasons, including explicit missing evidence.

Do not store credentials. Store evidence before permitting promotion. Acceptance
requires every host-required check to pass and child termination to be proven.
An empty required-check policy is invalid. Passing checks establish only the
properties tested, not general correctness or production readiness.

## Promotion boundary

The parent gatekeeper remains the only source-promotion path. Under exclusive
checkout access, immediately before PREPARED intent and Git writes, verify the
repository and branch identity, clean checkout, unchanged base commit, and exact
proposal manifest against accepted evidence. Reject stale, missing, altered, or
rejected evidence without touching parent files or index. Changes to check policy
also require re-verification. Do not accept agent-supplied verification IDs without
resolving and validating their stored host-owned evidence.

Link the accepted verification record to PREPARED intent and the resulting commit
outcome. Preserve existing crash reconciliation: Git and SQLite are not atomic.
Recovery must validate that an applied commit matches the accepted proposal;
ambiguous evidence remains unresolved. A later reflection failure cannot erase a
successful commit or its verification history.

## Required demonstrations

Use temporary Git repositories and vaults to test successful verification and
promotion, failing checks, timeout, cancellation, missing checks, changed policy,
stale base revisions, altered content or messages, and forged evidence linkage.
Assert parent HEAD, files, and index remain unchanged on rejection. Test failures
between evidence storage, PREPARED intent, Git commit, and outcome storage.

Real-container checks must demonstrate that proposed code cannot write to the
parent checkout or access its Git credentials or Docker socket. Retain container
identity and termination evidence. Demonstrate one passing proposal producing a
commit with linked verification and session records. Mocked execution alone does
not complete Phase 10; update PROJECT.md only for the scope actually verified.
