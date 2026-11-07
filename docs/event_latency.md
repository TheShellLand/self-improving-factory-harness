# Live event latency measurement protocol

Status: Phase 8 measurement design. This document records no live measurements
and does not validate the former sub-50 ms claim. Host receipt timing already
exists; actual transport latency remains unverified.

## Define the measurement

Report separate quantities with explicit units:

- Operation duration: host monotonic time from request dispatch to validated final
  result or failure, including provider retries within the operation.
- Time to first event: host monotonic time from dispatch to the first received
  protocol event, identifying that event's type.
- Inter-event interval: difference between consecutive host receipt timestamps.
- Source-to-host latency: time between production of an identified event at the
  source and receipt of that same event at the host.

The first three quantities do not establish source-to-host latency. Provider
inference time, batching, and idle periods affect receipt intervals. Do not label
those intervals network latency or use them to substantiate a sub-50 ms claim.
Specify the receipt boundary: complete JSONL record available, decoded record, or
callback invocation. Do not mix boundaries in one distribution.

## Clock and correlation requirements

Use a monotonic host clock for local durations. Never subtract monotonic values
from different processes or machines without a demonstrated common clock domain.
A source-to-host result requires source instrumentation, unique event correlation,
and a documented clock relationship. If synchronized wall clocks are used, retain
clock offset and uncertainty estimates before and after the run. Include that
uncertainty in reported bounds. Negative or ambiguous samples are invalid and
must be counted and explained rather than clipped to zero.

Without source timestamps and a validated clock relationship, mark transport
latency unavailable and report only the supported host measurements. An RPC
request/response round trip is a separate metric; halving it does not establish
one-way event latency.

## Reproducible collection

Use the documented live-check workflow in the runtime and pi client guides.
Retain source revision, pi version, provider/model identifiers, host and transport
kind, nonsecret execution settings, event limits, and the session and issue IDs.
Record whether execution is host-based or container-based. Do not mix warmup,
reconnect, retry, or different transport runs without explicit grouping.

Choose the sample count and run count before collection. Record every attempted
run, including failures, timeout, cancellation, and output-budget exhaustion.
Keep ordered event identifiers and receipt timestamps linked to retained session
evidence. Source instrumentation, when available, must preserve event ordering
and identify any added overhead. Never persist credentials or provider secrets.

## Analysis and acceptance

Report sample counts, missing or invalid samples, event-type groups, minimum,
median, p95, p99, and maximum. State the percentile calculation convention and
avoid strong tail claims from small samples. Keep failed runs visible separately;
do not silently remove slow observations or retries from a claimed distribution.

A claimed threshold must name the metric, event population, percentile or maximum,
clock uncertainty, and tested environment. Evidence from one environment does not
establish a universal guarantee. Publish a machine-readable summary alongside
raw retained timing evidence and a reproducible analysis command.

Before implementing analysis, inspect automonisaur for reusable statistics and
clock helpers. Test empty and singleton input, ordering errors, duplicate event
identifiers, nonfinite values, missing source timing, clock uncertainty, and
percentile calculation. Verify analysis cannot mutate the retained vault.

Complete the live measurement task only after an actual run and reproducible
analysis support the reported metric. If only receipt intervals are available,
leave source-to-host latency unchecked in PROJECT.md and state the instrumentation
needed to finish it. This protocol alone completes only measurement design.
