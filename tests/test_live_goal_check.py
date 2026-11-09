import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.coordinator import ExecutionOutcome
from core.config import PiAgentConfig
from scripts.check_live_pi import LivePiCheck, LivePiCheckConfig


class LiveGoalCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_helper_retains_two_iteration_evidence(self):
        class Client:
            config = PiAgentConfig()
            calls = 0

            async def run_structured(self, prompt, *, on_event):
                self.calls += 1
                on_event({"type": "agent_settled", "aborted": False})
                return ExecutionOutcome(success=True, summary="41" if self.calls == 1 else "42")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "check"
            with patch("scripts.check_live_pi.PiClient", Client):
                await LivePiCheck(LivePiCheckConfig(root, goal=True)).run()
            self.assertTrue((root / "evidence.json").is_file())

    async def test_immediate_correct_answer_does_not_prove_iteration(self):
        class Client:
            config = PiAgentConfig()

            async def run_structured(self, prompt, *, on_event):
                on_event({"type": "agent_settled", "aborted": False})
                return ExecutionOutcome(success=True, summary="42")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "check"
            with patch("scripts.check_live_pi.PiClient", Client):
                with self.assertRaisesRegex(RuntimeError, "did not demonstrate correction"):
                    await LivePiCheck(LivePiCheckConfig(root, goal=True)).run()
            self.assertTrue((root / "evidence.json").is_file())
