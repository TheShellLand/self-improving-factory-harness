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
