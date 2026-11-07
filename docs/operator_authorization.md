# Operator authorization acceptance contract

Status: Phase 14 design; production authentication is not implemented. The
[deployment guide](deployment.md) retains the current local-access restriction.
The recovery actor callback is an integration boundary, not an identity provider.

## Identity and permissions

The host authenticates requests before resolving permissions. Select and document
one deployment identity mechanism before implementation. Validate its credentials
using the mechanism's documented issuer, audience, expiration, and revocation
rules where applicable. Reject missing or invalid credentials; never derive an
operator identity from a request body, query parameter, or untrusted proxy header.
Only explicitly trusted proxies may supply identity headers, and direct backend
access must not permit impersonation through those headers.

Define separate permissions for reading audit data, submitting issues, voting,
selecting work, controlling scheduling, recovering sessions/proposals, retrying
issues, and activating/restoring strategies. Deny permissions not explicitly
granted. Authentication alone must not authorize recovery. Apply checks in backend
routes and shared service entry points used by other callers; browser button
visibility cannot enforce permissions.

Protect observations and artifacts as potentially sensitive model content.
Define authorization for inspection and downloads as well as mutations. A permitted
operator action still must satisfy state-transition and execution-stop checks.
Do not let an administrative role bypass uncertain termination or proposal evidence.

## Browser and deployment boundary

For cookie-based authentication, require appropriate secure cookie settings and
CSRF protection for mutations. Validate request origins under the selected policy;
CORS alone is not authorization. For bearer credentials, keep tokens out of URLs,
logs, audit payloads, and model context. Require encrypted transport outside the
explicitly local development boundary. Configuration classes retrieve credentials
from environment variables without trimming or changing their values.

Specify session expiry and revocation behavior, trusted proxy configuration, and
which health endpoints can be unauthenticated. API documentation and schema access
must follow an explicit policy. Identity-provider outages deny protected operations;
missing authentication configuration cannot silently enable public mutations.

## Audit and acceptance

Record stable authenticated actor identity, action, target, reason where required,
and outcome without credentials. Commit successful state changes with their audit
records. Denied attempts must not mutate the target; report audit delivery failures
without accidentally granting the action. Distinguish unauthenticated requests,
insufficient permission, unavailable adapters, and rejected state transitions.

Test every protected route directly, not just through the UI: anonymous access,
invalid/expired credentials, insufficient permission, forged actor fields, proxy
header spoofing, revoked access, and provider failure. Verify browser CSRF behavior
for the selected mechanism. Test that authorized recovery still fails when execution
state is unknown, and that audit insertion failure rolls back successful mutations.

Retain a deployment demonstration of authenticated inspection, allowed and denied
mutations, revocation, and recovery with a verified stopped worker. Inspect
reusable automonisaur clients before implementation. This contract does not select
an identity provider or establish that the current API meets these requirements.
