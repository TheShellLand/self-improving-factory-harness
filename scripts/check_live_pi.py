"""Run one harmless live model issue and retain an isolated audit vault."""
import argparse
import asyncio
import json
from pathlib import Path
import time

from core.coordinator import Coordinator
from core.database import initialize_database
from core.evolution import EvolutionEngine
from core.hotloader import HotLoaderModule
from core.pi_client import PiClient
from core.pi_runner import PiRunner
from core.vault import Vault
from core.goal import GoalConfig, TextGoalRunner
from core.goal_store import GoalStore


class LivePiCheckConfig:
    def __init__(self, directory, *, goal=False):
        self.directory = Path(directory)
        self.goal = goal


class LivePiCheck:
    def __init__(self, config):
        self.config = config

    async def run(self):
        root = self.config.directory
        root.mkdir(parents=True, exist_ok=False)
        database = root / "vault.db"
        initialize_database(database)
        vault = Vault(database)
        description = (
            "Compute 17 + 25. Return success true and summary exactly 42. "
            "Return empty observations and file_changes arrays and an empty commit_message.")
        if self.config.goal:
            description = (
                "Exercise host goal verification. On host_goal iteration 1 return success true "
                "and summary exactly 41, an intentionally incorrect draft. On subsequent "
                "iterations correct the draft: compute 17 + 25 and return success true and "
                "summary exactly 42. Return empty observations and file_changes and an empty commit_message.")
        vault.create_issue({"title": "Live arithmetic check", "description": description})
        client = PiClient()
        runner = PiRunner(client, vault=vault)
        if self.config.goal:
            runner = TextGoalRunner(runner, vault, {"answer": "Summary must equal 42"},
                {"answer": lambda text: text == "42"},
                GoalConfig(timeout=client.config.timeout * 3, max_iterations=3),
                goal_store=GoalStore(vault))
        coordinator = Coordinator(vault, runner,
                                  EvolutionEngine(database, lambda *_: None),
                                  HotLoaderModule(database))
        started = time.monotonic()
        try:
            await coordinator.run_once()
        finally:
            with vault.database.connect() as connection:
                signals = [dict(row) for row in connection.execute("SELECT * FROM trace_signals ORDER BY rowid")]
                sessions = [dict(row) for row in connection.execute("SELECT * FROM agent_sessions")]
            for signal in signals:
                signal["payload"] = json.loads(signal["payload"])
                signal["metadata"] = json.loads(signal["metadata"])
            evidence = {"duration_seconds": time.monotonic() - started,
                        "issues": vault.list_issues(), "sessions": sessions, "signals": signals}
            (root / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        session = sessions[0]
        if self.config.goal:
            checks = [s["payload"] for s in signals if s["source_agent"] == "goal"
                      and "verification" in s["payload"]]
            state = GoalStore(vault).inspect(session["session_id"])
            if (len(checks) < 2 or checks[0]["verification"] != {"answer": False}
                    or checks[-1]["verification"] != {"answer": True}
                    or state["status"] != "VERIFIED"):
                raise RuntimeError("Live goal did not demonstrate correction; inspect retained evidence")
        events = [s for s in signals if s["source_agent"] == "pi"]
        if (session["status"] != "COMPLETED" or session["execution_summary"] != "42"
                or not events or not any(s["payload"]["event"].get("type") == "agent_settled"
                                        for s in events)):
            raise RuntimeError("Live issue did not meet verification criteria; inspect retained evidence")
        print(json.dumps({"session_id": session["session_id"], "events": len(events),
                          "summary": session["execution_summary"], "directory": str(root),
                          "duration_seconds": evidence["duration_seconds"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="New directory for retained evidence")
    parser.add_argument("--goal", action="store_true", help="Verify a two-iteration text goal")
    args = parser.parse_args()
    asyncio.run(LivePiCheck(LivePiCheckConfig(args.directory, goal=args.goal)).run())
