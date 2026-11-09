import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from core.database import DatabaseClient
from core.vault import Vault
from core.goal import TextGoalRunner
from core.goal_store import GoalStore
from core.coordinator import ExecutionOutcome


class GoalStoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "vault.db"
        DatabaseClient(self.path).initialize()
        self.vault = Vault(self.path)
        self.vault.create_issue({"title": "Goal", "description": "Return 42"})
        self.issue, self.session = self.vault.claim_next()
        self.store = GoalStore(self.vault)

    async def test_verified_state_survives_restart_and_rejects_duplicate(self):
        runner = TextGoalRunner(AsyncMock(side_effect=[
            ExecutionOutcome(success=True, summary="41"),
            ExecutionOutcome(success=True, summary="42")]), self.vault,
            {"answer": "42"}, {"answer": lambda text: text == "42"}, goal_store=self.store)
        self.assertTrue((await runner(self.issue, self.session, {})).success)
        reopened = GoalStore(Vault(self.path))
        state = reopened.inspect(self.session)
        self.assertEqual(state["status"], "VERIFIED")
        self.assertEqual(state["version"], 6)
        self.assertEqual(state["requirements"], {"answer": "42"})
        with self.assertRaisesRegex(ValueError, "already started"):
            await runner(self.issue, self.session, {})
        self.assertEqual(runner.runner.await_count, 2)

    async def test_cancellation_preserves_claim_and_goal(self):
        runner = TextGoalRunner(AsyncMock(side_effect=asyncio.CancelledError), self.vault,
            {"answer": "42"}, {"answer": lambda text: True}, goal_store=self.store)
        with self.assertRaises(asyncio.CancelledError):
            await runner(self.issue, self.session, {})
        self.assertEqual(GoalStore(Vault(self.path)).inspect(self.session)["status"], "RUNNING")
        self.assertIsNone(Vault(self.path).claim_next())

    def test_stale_progress_and_terminal_updates_rejected(self):
        goal_id, version = self.store.begin(self.session, self.issue["issue_id"], {"a": "a"})
        version2 = self.store.append(self.session, goal_id, version, {"iteration": 1})
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.store.append(self.session, goal_id, version, {"iteration": 2})
        self.store.append(self.session, goal_id, version2, {"goal_stop": "incomplete"})
        with self.assertRaisesRegex(ValueError, "terminal"):
            self.store.append(self.session, goal_id, version2 + 1, {"iteration": 3})

    def test_audit_failure_rolls_back_progress(self):
        goal_id, version = self.store.begin(self.session, self.issue["issue_id"], {"a": "a"})
        with patch.object(self.vault, "_record", side_effect=RuntimeError("disk")):
            with self.assertRaises(RuntimeError):
                self.store.append(self.session, goal_id, version, {"goal_stop": "verified"})
        self.assertEqual(self.store.inspect(self.session)["version"], version)
        self.assertEqual(self.store.inspect(self.session)["status"], "RUNNING")

    def test_wrong_claim_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "active issue claim"):
            self.store.begin(self.session, "wrong", {"a": "a"})
        self.assertIsNone(self.store.inspect(self.session))

    def test_initialize_preserves_goal(self):
        self.store.begin(self.session, self.issue["issue_id"], {"a": "a"})
        DatabaseClient(self.path).initialize()
        self.assertEqual(self.store.inspect(self.session)["status"], "RUNNING")
