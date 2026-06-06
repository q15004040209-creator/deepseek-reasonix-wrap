"""
DeepSeek-Reasonix Python Wrapper
Wraps the DeepSeek-Reasonix Go binary as a Python SDK.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional


@dataclass
class ToolDefinition:
    """Definition of a tool available to the Reasonix agent."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable[[Dict[str, Any]], Any] = None


@dataclass
class ReasonixConfig:
    """Configuration for the Reasonix agent session."""
    project_path: str
    default_model: str = "deepseek-flash"
    planner_model: Optional[str] = None
    auto_plan: str = "off"
    subagent_model: Optional[str] = None
    api_key: Optional[str] = None
    extra_env: Dict[str, str] = field(default_factory=dict)


class ReasonixAgent:
    """
    Python wrapper for DeepSeek-Reasonix.

    Launches the reasonix Go binary as a subprocess and communicates
    with it via its stdin/stdout JSON-RPC interface.

    Usage:
        agent = ReasonixAgent(project_path="/path/to/project")
        for chunk in agent.run("implement login"):
            print(chunk, end="")
    """

    def __init__(
        self,
        project_path: str,
        model: str = "deepseek-flash",
        planner_model: Optional[str] = None,
        auto_plan: str = "off",
        subagent_model: Optional[str] = None,
        api_key: Optional[str] = None,
        extra_env: Optional[Dict[str, str]] = None,
        binary_path: Optional[str] = None,
    ):
        self.project_path = os.path.abspath(project_path)
        self.model = model
        self.planner_model = planner_model
        self.auto_plan = auto_plan
        self.subagent_model = subagent_model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.extra_env = extra_env or {}
        self.binary_path = binary_path or self._find_binary()
        self._tools: Dict[str, ToolDefinition] = {}
        self._proc: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._response_buffer: str = ""
        self._buffer_lock = threading.Lock()

    def _find_binary(self) -> str:
        """Look for reasonix binary in PATH or common locations."""
        import shutil
        binary = shutil.which("reasonix")
        if binary:
            return binary

        # Fallback: check common install locations
        for candidate in [
            os.path.expanduser("~/.local/bin/reasonix"),
            os.path.expanduser("~/go/bin/reasonix"),
            "/usr/local/bin/reasonix",
        ]:
            if os.path.isfile(candidate):
                return candidate

        # Return "reasonix" and let subprocess discover it
        return "reasonix"

    def _build_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env.update(self.extra_env)
        if self.api_key:
            env["DEEPSEEK_API_KEY"] = self.api_key
        return env

    def _write_request(self, proc: subprocess.Popen, method: str, params: Dict[str, Any]) -> None:
        """Write a JSON-RPC request to reasonix stdin."""
        request = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        proc.stdin.write(json.dumps(request).encode("utf-8") + b"\n")
        proc.stdin.flush()

    def _read_response(self, proc: subprocess.Popen) -> Iterator[str]:
        """Yield response lines from reasonix stdout."""
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            yield line

    def _start_process(self) -> subprocess.Popen:
        """Start the reasonix subprocess."""
        env = self._build_env()

        args = [
            self.binary_path,
            "chat",
        ]
        if self.planner_model:
            args.extend(["--planner-model", self.planner_model])
        if self.subagent_model:
            args.extend(["--subagent-model", self.subagent_model])
        if self.auto_plan != "off":
            args.extend(["--auto-plan", self.auto_plan])

        proc = subprocess.Popen(
            args,
            cwd=self.project_path,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return proc

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool available to the agent."""
        self._tools[tool.name] = tool

    def run(self, task: str, timeout: Optional[int] = None) -> str:
        """
        Run a task synchronously and return the full response.

        Args:
            task: The task description for the agent
            timeout: Optional timeout in seconds

        Returns:
            The agent's full response as a string
        """
        chunks = []
        for chunk in self.run_stream(task, timeout=timeout):
            chunks.append(chunk)
        return "".join(chunks)

    def run_stream(self, task: str, timeout: Optional[int] = None) -> Iterator[str]:
        """
        Run a task and yield response chunks as they arrive.

        Args:
            task: The task description for the agent
            timeout: Optional timeout in seconds

        Yields:
            Response text chunks
        """
        proc = self._start_process()

        try:
            self._write_request(proc, "run", {"task": task})
            for line in self._read_response(proc):
                try:
                    data = json.loads(line)
                    if "result" in data:
                        yield data["result"]
                    elif "error" in data:
                        yield f"[ERROR] {data['error']}"
                        break
                except json.JSONDecodeError:
                    yield line.rstrip("\n")
        finally:
            proc.stdin.close()
            proc.wait(timeout=timeout or 60)

    async def run_async(self, task: str, timeout: Optional[int] = None) -> str:
        """Async version of run()."""
        return await asyncio.to_thread(self.run, task, timeout)

    async def run_stream_async(self, task: str, timeout: Optional[int] = None) -> AsyncIterator[str]:
        """Async version of run_stream()."""
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        async def producer():
            for chunk in self.run_stream(task, timeout=timeout):
                await queue.put(chunk)
            await queue.put(None)

        async def consumer():
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item

        await asyncio.create_task(producer())
        async for chunk in consumer():
            yield chunk

    def chat(self, message: str) -> str:
        """Send a single chat message and return the response."""
        return self.run(message)


# ─────────────────────────────────────────────────────────────────────────────
# TypeScript-originated demo (also usable as ESM)
# ─────────────────────────────────────────────────────────────────────────────

def demo_python():
    """Demonstrates the Python SDK usage."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
       print("⚠️  Set DEEPSEEK_API_KEY environment variable to run this demo")
        return

    agent = ReasonixAgent(
        project_path=os.getcwd(),
        model="deepseek-flash",
        auto_plan="on",
    )

    print("🧠 DeepSeek-Reasonix Python Demo")
    print("─" * 40)
    print("Agent initialized. Type 'exit' to quit.\n")

    while True:
        task = input("You: ")
        if task.lower() in ("exit", "quit", "q"):
            break
        if not task.strip():
            continue

        print("Agent: ", end="", flush=True)
        response = agent.run(task, timeout=120)
        print(response)
        print()


if __name__ == "__main__":
    demo_python()