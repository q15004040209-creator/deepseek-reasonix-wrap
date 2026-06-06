# deepseek-reasonix-wrap

> Python/TypeScript wrapper for **[DeepSeek-Reasonix](https://github.com/esengine/DeepSeek-Reasonix)** — a DeepSeek-native AI coding agent for your terminal, engineered around prefix-cache stability.

## What is DeepSeek-Reasonix?

DeepSeek-Reasonix is a Go-based AI coding agent that connects to DeepSeek models (and any OpenAI-compatible endpoint). It leverages **prefix-cache** so token costs stay low across long sessions. The agent reads a `reasonix.toml` config file, spawns tools as subprocesses over stdin/stdout JSON-RPC (MCP-compatible), and drives a terminal TUI.

**Key features:**
- Config-driven: providers, tools, and plugins declared in `reasonix.toml`
- Multi-model & composable: DeepSeek (flash/pro) and MiMo ship as presets; any OpenAI-compatible endpoint works
- Plugin-driven: external tools run as subprocesses over JSON-RPC
- Zero-friction distribution: single Go binary (`cgo_enabled=0`) cross-compiles to 6 targets
- Prefix-cache stable: designed for long-running sessions

## What This Wrap Provides

This wrapper gives you a **Python SDK** and **TypeScript SDK** to programmatically launch and interact with DeepSeek-Reasonix agents from your own code — without spawning a sub-process TUI. You can:

- Launch a reasonix session with a custom prompt
- Stream agent responses
- Parse and handle tool-call results
- Integrate into AI agent pipelines (LangChain, AutoGen, custom orchestration)

## Installation

```bash
# Python
pip install deepseek-reasonix-wrap

# Or from source
pip install .
```

```bash
# TypeScript / Node.js
npm install deepseek-reasonix-wrap
# or
yarn add deepseek-reasonix-wrap
```

## Python Demo

```python
import os
from deepseek_reasonix_wrap import ReasonixAgent

# Set your DeepSeek API key
os.environ["DEEPSEEK_API_KEY"] = "sk-your-key-here"

# Initialize the agent with a custom project directory
agent = ReasonixAgent(
    project_path="/path/to/your/project",
    model="deepseek-flash",
    auto_plan="on", # Enable automatic planning
)

# Run a task and stream the response
for chunk in agent.run("Implement a REST API endpoint for user login"):
    print(chunk, end="", flush=True)

# Run with a specific planner model
result = agent.run(
    task="add unit tests for the auth module",
    planner_model="deepseek-pro",
    timeout=120,
)
print(result)
```

### Advanced: Tool Registration

```python
from deepseek_reasonix_wrap import ReasonixAgent, ToolDefinition

agent = ReasonixAgent(project_path="/path/to/project")

# Register a custom tool available to the agent
agent.register_tool(
    name="fetch_jira",
    description="Fetch a JIRA ticket by ID",
    input_schema={"type": "object", "properties": {"ticket_id": {"type": "string"}}},
    handler=lambda params: {"id": params["ticket_id"], "status": "Open", "summary": "Sample ticket"}
)

# Now the agent can call fetch_jira during its reasoning
for chunk in agent.run("Check the status of JIRA-123"):
    print(chunk, end="", flush=True)
```

### Advanced: Multi-Model Session

```python
from deepseek_reasonix_wrap import ReasonixAgent

agent = ReasonixAgent(
    project_path="/path/to/project",
    default_model="deepseek-flash",
)

# Run executor + planner in separate model sessions (cache-stable)
result = agent.run_with_planner(
    task="redesign the database schema",
    executor_model="deepseek-flash",
    planner_model="deepseek-pro",
)
print(result)
```

## TypeScript Demo

```typescript
import { ReasonixAgent } from 'deepseek-reasonix-wrap';

const agent = new ReasonixAgent({
  projectPath: '/path/to/your/project',
  model: 'deepseek-flash',
  autoPlan: true,
  env: {
    DEEPSEEK_API_KEY: process.env.DEEPSEEK_API_KEY,
  },
});

// Stream responses
for await (const chunk of agent.run('Implement a todo list feature')) {
  process.stdout.write(chunk);
}
```

### Advanced: Tool Registration (TypeScript)

```typescript
import { ReasonixAgent, ToolDefinition } from 'deepseek-reasonix-wrap';

const agent = new ReasonixAgent({
  projectPath: '/path/to/project',
  model: 'deepseek-flash',
});

agent.registerTool({
  name: 'search_docs',
  description: 'Search documentation by keyword',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string' },
      limit: { type: 'number', default: 5 },
    },
    required: ['query'],
  },
  handler: async ({ query, limit = 5 }) => {
    // Your implementation here
    return { results: [`Result for "${query}"`, /* ... */].slice(0, limit) };
  },
});

for await (const chunk of agent.run('Find docs about authentication')) {
  process.stdout.write(chunk);
}
```

## Configuration

Create a `reasonix.toml` in your project root:

```toml
default_model = "deepseek-flash"

[agent]
# planner_model = "deepseek-pro"  # Optional separate planner
# auto_plan = "off"              # Manual plan mode
# subagent_model = "deepseek-pro"

[[providers]]
name = "deepseek"
api_key_env = "DEEPSEEK_API_KEY" # Never hardcoded

[tools]
# Built-in + custom tools registered via SDK
```

## Original Project

- **GitHub:** https://github.com/esengine/DeepSeek-Reasonix
- **Docs:** https://docs.reasonix.ai
- **License:** MIT

## License

MIT License — see original project for details.