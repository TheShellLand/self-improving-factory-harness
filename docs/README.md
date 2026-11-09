# SIFH documentation map

[PROJECT.md](../PROJECT.md) is the progress ledger. A written acceptance contract
specifies future behavior; it does not establish implementation or live verification.
Use each guide's evidence and limitations when assessing readiness.

## Existing setup and component guides

| Guide | Purpose |
| --- | --- |
| [Runtime](runtime_guide.md) | Environment, Docker helpers, verification commands, and Git boundaries |
| [Deployment](deployment.md) | API startup, persistent volumes, replacement, and current access restrictions |
| [Automonisaur reuse](automonisaur.md) | Reuse decisions and config/client conventions |
| [Pi client](pi_client.md) | Implemented host RPC client, runner, event persistence, and live-check helper |
| [Recovery](recovery.md) | Existing recovery service and API; production adapters remain pending |
| [Strategy evaluation](strategy_evaluation.md) | Fixed suite, implemented collection/scoring, evidence verification, and adoption limits |

## Acceptance contracts for remaining work

| Phase | Contract | Remaining implementation or evidence |
| --- | --- | --- |
| 8 | [Goal completion](goal_completion.md) | Host-owned goal state, bounded iteration, and live multi-step verification |
| 8 | [Event latency](event_latency.md) | Live measurement and valid source/host clock correlation |
| 9 | [Docker RPC](docker_rpc.md) | Bidirectional transport, bounded lifecycle, and real-container issue execution |
| 10 | [Proposal verification](proposal_verification.md) | Isolated checks and exact-evidence promotion enforcement |
| 11 | [Scheduling](scheduling.md) | Durable exclusive admission, controls, and restart recovery |
| 12 | [Strategy activation](strategy_activation.md) | Atomic adoption and complete snapshot restoration |
| 14 | [Operator authorization](operator_authorization.md) | Production identity integration and backend permission enforcement |
| 14 | [Execution stop](execution_stop.md) | Host/child identity verification and fencing against new launches |
| 14 | [Backup and restore](backup_restore.md) | Consistent capture and verified isolated restoration |

Follow PROJECT.md dependencies when implementing these contracts. In particular,
a scheduler or browser control must not bypass unresolved execution, authorization,
or proposal verification boundaries. Run the verification appropriate to the actual
change and record only the scope supported by retained results.
