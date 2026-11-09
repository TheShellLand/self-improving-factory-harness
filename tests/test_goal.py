import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from core.coordinator import ExecutionOutcome
from core.goal import GoalConfig, TextGoalRunner


class TextGoalTests(unittest.IsolatedAsyncioTestCase):
    def runner(self, answers, **kwargs):
        transport = AsyncMock(side_effect=[ExecutionOutcome(success=True, summary=a) for a in answers])
        vault = Mock()
        return TextGoalRunner(transport, vault, {"answer": "Return 42"},
                              {"answer": lambda text: text == "42"}, **kwargs)

    async def test_early_success_requires_another_iteration(self):
        runner = self.runner(["41", "42"])
        result = await runner({"issue_id": "issue"}, "session", {})
        self.assertTrue(result.success)
        self.assertEqual(runner.runner.await_count, 2)
        context = runner.runner.await_args_list[1].args[2]
        self.assertEqual(context["host_goal"]["previous"]["verification"], {"answer": False})

    async def test_iteration_limit(self):
        runner = self.runner(["41"], config=GoalConfig(max_iterations=1))
        self.assertFalse((await runner({"issue_id": "issue"}, "session", {})).success)

    async def test_unknown_requirement_never_invokes_agent(self):
        runner = self.runner([])
        runner._verifiers.clear()
        self.assertFalse((await runner({"issue_id": "issue"}, "session", {})).success)
        runner.runner.assert_not_awaited()

    async def test_storage_failure_propagates(self):
        runner = self.runner(["42"])
        runner.vault.record.side_effect = RuntimeError("storage")
        with self.assertRaisesRegex(RuntimeError, "storage"):
            await runner({"issue_id": "issue"}, "session", {})
        runner.runner.assert_not_awaited()

    async def test_cancellation_propagates(self):
        runner = self.runner([])
        runner.runner.side_effect = asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await runner({"issue_id": "issue"}, "session", {})

    async def test_output_bound(self):
        runner = self.runner(["42"], config=GoalConfig(max_result_bytes=1))
        self.assertFalse((await runner({"issue_id": "issue"}, "session", {})).success)

    def test_invalid_config(self):
        for options in ({"timeout": float("nan")}, {"max_iterations": True},
                        {"no_progress_limit": 0}):
            with self.assertRaises(ValueError):
                GoalConfig(**options)

    async def test_storage_timeout_is_not_goal_deadline(self):
        runner = self.runner(["42"])
        runner.vault.record.side_effect = [None, TimeoutError("storage unavailable")]
        with self.assertRaisesRegex(TimeoutError, "storage unavailable"):
            await runner({"issue_id": "issue"}, "session", {})
        self.assertEqual(runner.vault.record.call_count, 2)

    async def test_transport_timeout_propagates(self):
        runner = self.runner([])
        runner.runner.side_effect = TimeoutError("transport")
        with self.assertRaisesRegex(TimeoutError, "transport"):
            await runner({"issue_id": "issue"}, "session", {})

    async def test_deadline_waits_for_runner_cleanup(self):
        cleaned = asyncio.Event()
        async def blocked(*args):
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        runner = self.runner([], config=GoalConfig(timeout=0.01))
        runner.runner.side_effect = blocked
        result = await runner({"issue_id": "issue"}, "session", {})
        self.assertFalse(result.success)
        self.assertEqual(result.summary, "Goal deadline exceeded")
        self.assertTrue(cleaned.is_set())

    async def test_final_summary_rechecks_all_requirements(self):
        runner = self.runner(["a", "b"], config=GoalConfig(max_iterations=2))
        runner._requirements = {"a": "Contains a", "b": "Contains b"}
        runner._verifiers = {"a": lambda text: "a" in text,
                             "b": lambda text: "b" in text}
        result = await runner({"issue_id": "issue"}, "session", {})
        self.assertFalse(result.success)
        checks = [call.args[0].payload["verification"]
                  for call in runner.vault.record.call_args_list
                  if "verification" in call.args[0].payload]
        self.assertEqual(checks, [{"a": True, "b": False}, {"a": False, "b": True}])

    async def test_verifier_errors_and_truthy_values_fail(self):
        for verifier in (Mock(side_effect=ValueError("invalid")), lambda text: 1):
            runner = self.runner(["42"], config=GoalConfig(max_iterations=1))
            runner._verifiers["answer"] = verifier
            self.assertFalse((await runner({"issue_id": "issue"}, "session", {})).success)

    async def test_no_progress_stops_before_iteration_limit(self):
        runner = self.runner(["41"] * 5, config=GoalConfig(no_progress_limit=1))
        result = await runner({"issue_id": "issue"}, "session", {})
        self.assertEqual(result.summary, "Goal made no progress")
        self.assertEqual(runner.runner.await_count, 2)
