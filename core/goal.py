"""Bounded, host-verified text goals; source proposals are deliberately rejected."""
import asyncio
import copy
import json
import math
from dataclasses import dataclass

from core.coordinator import ExecutionOutcome
from core.signals import SignalPulse


@dataclass(frozen=True)
class GoalConfig:
    max_iterations: int = 5
    timeout: float = 120
    max_result_bytes: int = 65536
    no_progress_limit: int = 2

    def __post_init__(self):
        for name in ("max_iterations", "max_result_bytes", "no_progress_limit"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.timeout) not in (int, float) or not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("timeout must be finite and positive")


class TextGoalRunner:
    """Host supplies immutable requirement text and synchronous pure verifiers.

    Verifiers receive the final summary and must return a literal bool. They
    must not perform blocking I/O. The wrapped runner owns transport cleanup.
    Cancellation and storage errors propagate to the coordinator.
    """

    def __init__(self, runner, vault, requirements, verifiers, config=None, *, goal_store=None):
        if not requirements or any(type(k) is not str or not k or
                                   type(v) is not str or not v for k, v in requirements.items()):
            raise ValueError("Nonempty named requirements are required")
        self.runner, self.vault = runner, vault
        self._requirements = dict(requirements)
        self._verifiers = dict(verifiers)
        self.config = config or GoalConfig()
        self.goal_store = goal_store

    async def __call__(self, issue, session_id, config):
        goal_id = None
        version = None
        if self.goal_store is not None:
            goal_id, version = self.goal_store.begin(session_id, issue["issue_id"], self._requirements)

        def record(payload):
            nonlocal version
            if self.goal_store is not None:
                version = self.goal_store.append(session_id, goal_id, version, payload)
                return
            self.vault.record(SignalPulse(source_agent="goal", action_type="OBSERVATION",
                payload={**payload, "session_id": session_id, "issue_id": issue["issue_id"]}))

        def stop(reason):
            record({"goal_stop": reason})
            return ExecutionOutcome(success=False, summary=reason)

        if self.goal_store is None:
            record({"goal_version": 1, "requirements": self._requirements})
        if any(not callable(self._verifiers.get(k)) for k in self._requirements):
            return stop("Unsupported goal requirement")
        previous = None
        unchanged = 0
        feedback = None
        deadline = asyncio.timeout(self.config.timeout)
        try:
            async with deadline:
                for iteration in range(1, self.config.max_iterations + 1):
                    context = copy.deepcopy(config)
                    context["host_goal"] = {"requirements": dict(self._requirements),
                                            "iteration": iteration, "previous": feedback}
                    result = ExecutionOutcome.model_validate(
                        await self.runner(copy.deepcopy(issue), session_id, context))
                    encoded = result.model_dump_json()
                    if len(encoded.encode()) > self.config.max_result_bytes:
                        return stop("Goal result output limit exceeded")
                    record({"iteration": iteration, "result": json.loads(encoded)})
                    if result.file_changes:
                        return stop("Text goals cannot verify source proposals")
                    checks = {}
                    for key in self._requirements:
                        try:
                            passed = self._verifiers[key](result.summary)
                            checks[key] = passed is True
                        except Exception:
                            checks[key] = False
                    record({"iteration": iteration, "verification": checks})
                    if result.success and all(checks.values()):
                        record({"goal_stop": "verified", "iteration": iteration})
                        return result
                    progress = (result.summary, tuple(checks.items()))
                    unchanged = unchanged + 1 if progress == previous else 0
                    if unchanged >= self.config.no_progress_limit:
                        return stop("Goal made no progress")
                    previous = progress
                    feedback = {"summary": result.summary, "verification": checks}
                return stop("Goal iteration limit exceeded")
        except TimeoutError:
            if not deadline.expired():
                raise
            return stop("Goal deadline exceeded")
