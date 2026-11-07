# Docker RPC lifecycle acceptance contract

This contract defines the remaining Phase 9 transport milestone. The agent image
and offline smoke helper exist; the production transport described here remains
unimplemented. See [runtime setup](runtime_guide.md) for existing helpers and
[pi RPC semantics](pi_client.md) for the supported host protocol.

## Ownership and isolation

The host owns container creation, identity, deadlines, event persistence, and
termination. Persist a session-to-container identity before starting execution,
so a host restart can discover and stop the exact child. Use a unique container
name and host-selected labels; never accept identity from model output. Record
the resolved image ID as execution evidence.

The child runs as an unprivileged user without the Docker socket, parent checkout
mounts, or host pi configuration directories. The first milestone is text-only:
no repository mount is required. Keep the image's disabled tools, extensions,
skills, templates, themes, and session persistence settings. The host selects
network access required by the provider; offline checks retain networking disabled.

A config class retrieves explicitly selected provider credentials from the host
environment. Forward only those names, preserving values exactly. Missing required
credentials fail before execution. Do not inherit the entire environment or
record credential values in argv, manifests, observations, or diagnostics.

## Transport and budgets

Use an interactive, non-TTY transport with separate stdin, stdout, and stderr.
TTY allocation must not merge diagnostics with JSONL protocol records. Stream
stdin requests and stdout responses concurrently, and drain stderr concurrently
with bounded retention. Handle partial records and split UTF-8 sequences without
assuming each read is a complete event.

Reuse the host client's response matching, structured-result validation, and
settlement rules. A successful command acknowledgment or `agent_end` cannot
complete an issue. Require the final successful assistant message and
`agent_settled`, then validate the structured result before returning it.

Configuration must bound record bytes, total stdout bytes, retained stderr bytes,
event count, execution time, and cleanup time. Reject nonpositive or nonfinite
limits before creating a container. Specify whether each overflow aborts or
truncates: protocol and event overflows abort; retained diagnostics may truncate
with an explicit marker. Continue draining diagnostics without growing memory.
The execution deadline includes container creation and startup; cleanup has its
own bounded deadline. Image acquisition is a separate setup operation.

Persist events through the existing session-linked recorder. Host-assigned issue
and session IDs remain authoritative. Failed storage aborts execution and starts
cleanup; events already written remain available. Receipt intervals are not
measurements of source-to-host latency.

## Termination and recovery

Every path after container creation attempts cleanup, including startup failure,
protocol error, provider failure, timeout, callback failure, and cancellation.
Cancellation must allow bounded cleanup to run before propagating. Closing the
Docker CLI process or observing its exit does not prove the container stopped.

Inspect the exact container through the host Docker client, terminate it if
needed, and confirm it is stopped or absent before declaring termination proven.
Retain exit status and cleanup evidence, then remove the container. Bound retries.
An unreachable daemon, failed inspection, or exhausted cleanup deadline means
termination is uncertain, not successful.

Uncertain termination must retain a durable execution blocker across restarts.
Do not let an ordinary FAILED session release admission while its child may still
run. Integration must either preserve the unresolved RUNNING claim or introduce
an equivalent durable blocker checked by claims and recovery. This requires
coordinator integration; raising an ordinary runner exception alone is inadequate.
Only the production stop verifier may clear uncertainty through the existing
operator-authorized recovery workflow. Never infer termination from record age.

## Verification evidence

Transport tests must cover fragmented records, malformed JSON, mismatched reply
IDs, early disconnect, provider failure, output overflow, storage failure, and
settlement ordering. Lifecycle tests must cover cancellation during creation,
startup, inference, and cleanup, plus daemon unavailability and failed removal.
Verify both bounded completion and retained evidence, including claim blocking
when termination is uncertain.

Run the documented agent build and offline RPC helpers before a real-container
integration check. Verify mounts, user, environment names, and container identity
without printing secrets. Demonstrate successful RPC, timeout, and cancellation
against actual containers and confirm no child remains running afterward.
Finally run one submitted issue with retained events and a validated final result,
without code promotion. Record source revision, image ID, session ID, outcomes,
and cleanup verification. Mocked tests and offline get_state alone do not satisfy
this live milestone.
