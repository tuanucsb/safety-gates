"""Stdio MCP server exposing the four case tools to the Claude Code CLI.

Launched by the CLI backend with the task instance selected through environment variables:
  ENGSAFE_TASK, ENGSAFE_VARIANT  - which instance to serve
  ENGSAFE_STATE                  - JSON file where docs_read and the submission are persisted,
                                   because the server runs in its own process.
  ENGSAFE_NO_LIST                - "1" for no-list policies: list_documents is not registered at all.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from .agent import ToolEnv
from .tasks import get

server = MCPServer("engsafe")
_env: ToolEnv | None = None
NO_LIST = os.environ.get("ENGSAFE_NO_LIST") == "1"


def _get_env() -> ToolEnv:
    global _env
    if _env is None:
        inst = get(os.environ["ENGSAFE_TASK"]).instance(os.environ["ENGSAFE_VARIANT"])
        _env = ToolEnv(inst, allow_list=not NO_LIST)
    return _env


def _persist() -> None:
    env = _get_env()
    Path(os.environ["ENGSAFE_STATE"]).write_text(
        json.dumps({"docs_read": env.docs_read, "submission": env.submission}))


def _run(name: str, args: dict) -> str:
    out, is_err = _get_env().run(name, args)
    _persist()
    if is_err:
        raise ToolError(out)
    return out


class Check(BaseModel):
    criterion: str = Field(description="The acceptance criterion evaluated.")
    value: float = Field(description="The value obtained.")
    unit: str
    comparator: str = Field(description="One of <=, >=, <, >.")
    limit: float = Field(description="The limit the value was compared against.")
    passes: bool = Field(description="Whether the value satisfies the limit.")


if not NO_LIST:
    @server.tool(structured_output=False,
                 description="List the documents available for this case, with a one-line title for each.")
    def list_documents() -> str:
        return _run("list_documents", {})


@server.tool(structured_output=False, description="Return the full text of one case document by its name (from list_documents).")
def read_document(name: str) -> str:
    return _run("read_document", {"name": name})


@server.tool(structured_output=False, description=("Evaluate an arithmetic expression and return the number. Supports + - * / ** ^, "
                          "parentheses, scientific notation, ln, log10, exp, sqrt, abs, min, max, sum, pi."))
def calculate(expression: str) -> str:
    return _run("calculate", {"expression": expression})


@server.tool(structured_output=False, description=("Record the final decision for the case. Call exactly once, at the end. "
                          "decision is APPROVE, REJECT or ESCALATE; checks lists each acceptance criterion "
                          "evaluated with value, unit, comparator, limit and pass/fail."))
def submit_decision(decision: str, checks: list[Check], rationale: str) -> str:
    if decision not in ("APPROVE", "REJECT", "ESCALATE"):
        raise ToolError("decision must be APPROVE, REJECT or ESCALATE")
    return _run("submit_decision", {"decision": decision, "checks": [c.model_dump() for c in checks],
                                    "rationale": rationale})


if __name__ == "__main__":
    server.run(transport="stdio")
