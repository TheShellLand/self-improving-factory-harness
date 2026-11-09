"""Durable admission and versioned observations for host-owned text goals."""
import json
from uuid import uuid4

from core.signals import SignalPulse


class GoalStore:
    def __init__(self, vault):
        self.vault = vault

    def begin(self, session_id, issue_id, requirements):
        encoded = json.dumps(requirements, allow_nan=False)
        goal_id = str(uuid4())
        with self.vault.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not connection.execute(
                "SELECT 1 FROM issue_runs r JOIN agent_sessions s USING(session_id) "
                "WHERE r.session_id = ? AND r.issue_id = ? AND s.status = 'RUNNING'",
                (session_id, issue_id)).fetchone():
                raise ValueError("Goal requires its active issue claim")
            if connection.execute("SELECT 1 FROM goal_runs WHERE session_id = ?",
                                  (session_id,)).fetchone():
                raise ValueError("Goal already started; automatic continuation is forbidden")
            connection.execute("INSERT INTO goal_runs VALUES (?, ?, ?, ?, 1, 'RUNNING', '{}')",
                               (session_id, goal_id, issue_id, encoded))
            self.vault._record(connection, SignalPulse(source_agent="goal", action_type="OBSERVATION",
                payload={"session_id": session_id, "issue_id": issue_id, "goal_id": goal_id,
                         "goal_version": 1, "requirements": requirements}))
        return goal_id, 1

    def append(self, session_id, goal_id, version, payload):
        encoded = json.dumps(payload, allow_nan=False)
        status = ("VERIFIED" if payload.get("goal_stop") == "verified" else
                  "INCOMPLETE" if "goal_stop" in payload else "RUNNING")
        with self.vault.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT issue_id FROM goal_runs WHERE session_id = ? "
                                     "AND goal_id = ? AND version = ? AND status = 'RUNNING'",
                                     (session_id, goal_id, version)).fetchone()
            if row is None:
                raise ValueError("Stale or terminal goal state")
            if not connection.execute("SELECT 1 FROM agent_sessions WHERE session_id = ? "
                                      "AND status = 'RUNNING'", (session_id,)).fetchone():
                raise ValueError("Goal session is no longer running")
            connection.execute("UPDATE goal_runs SET version = ?, status = ?, progress = ? "
                               "WHERE session_id = ?", (version + 1, status, encoded, session_id))
            self.vault._record(connection, SignalPulse(source_agent="goal", action_type="OBSERVATION",
                payload={**payload, "session_id": session_id, "issue_id": row["issue_id"],
                         "goal_id": goal_id, "goal_version": version + 1}))
        return version + 1

    def inspect(self, session_id):
        with self.vault.database.connect() as connection:
            row = connection.execute("SELECT * FROM goal_runs WHERE session_id = ?",
                                     (session_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        for key in ("requirements", "progress"):
            result[key] = json.loads(result[key])
        return result
