/**
 * DeepSeek-Reasonix TypeScript Wrapper
 * Wraps the DeepSeek-Reasonix Go binary as a TypeScript/Node.js SDK.
 */

export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler?: (params: Record<string, unknown>) => unknown;
}

export interface ReasonixAgentOptions {
  projectPath: string;
  model?: string;
  plannerModel?: string;
  autoPlan?: boolean;
  subagentModel?: string;
  apiKey?: string;
  binaryPath?: string;
  env?: Record<string, string>;
}

export interface JsonRpcRequest {
  jsonrpc: "2.0";
  method: string;
  params: Record<string, unknown>;
  id: number;
}

export interface JsonRpcResponse {
  jsonrpc: "2.0";
  result?: string;
  error?: { code: number; message: string };
  id: number;
}

export class ReasonixAgent {
  private projectPath: string;
  private model: string;
  private plannerModel?: string;
  private autoPlan: boolean;
  private subagentModel?: string;
  private apiKey?: string;
  private binaryPath: string;
  private env: Record<string, string>;
  private tools: Map<string, ToolDefinition> = new Map();

  constructor(options: ReasonixAgentOptions) {
    this.projectPath = options.projectPath;
    this.model = options.model ?? "deepseek-flash";
    this.plannerModel = options.plannerModel;
    this.autoPlan = options.autoPlan ?? false;
    this.subagentModel = options.subagentModel;
    this.apiKey = options.apiKey ?? process.env.DEEPSEEK_API_KEY;
    this.binaryPath = options.binaryPath ?? "reasonix";
    this.env = {
      ...process.env,
      ...(options.env ?? {}),
    };
    if (this.apiKey) {
      this.env["DEEPSEEK_API_KEY"] = this.apiKey;
    }
  }

  /**
   * Register a custom tool available to the agent.
   */
  registerTool(tool: ToolDefinition): void {
    this.tools.set(tool.name, tool);
  }

  /**
   * Run a task synchronously and return the full response.
   */
  async run(task: string, timeout = 120): Promise<string> {
    const chunks: string[] = [];
    for await (const chunk of this.runStream(task, timeout)) {
      chunks.push(chunk);
    }
    return chunks.join("");
  }

  /**
   * Run a task and yield response chunks as they arrive.
   */
  async *runStream(task: string, timeout = 120): AsyncIterable<string> {
    const { spawn } = await import("child_process");

    const args = ["chat"];
    if (this.plannerModel) {
      args.push("--planner-model", this.plannerModel);
    }
    if (this.subagentModel) {
      args.push("--subagent-model", this.subagentModel);
    }
    if (this.autoPlan) {
      args.push("--auto-plan", "on");
    }

    const proc = spawn(this.binaryPath, args, {
      cwd: this.projectPath,
      env: this.env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    let done = false;
    const timeoutId = setTimeout(() => {
      if (!done) {
        proc.kill();
      }
    }, timeout * 1000);

    try {
      // Send the task as a JSON-RPC request
      const request: JsonRpcRequest = {
        jsonrpc: "2.0",
        method: "run",
        params: { task },
        id: 1,
      };
      proc.stdin.write(JSON.stringify(request) + "\n");
      proc.stdin.end();

      for await (const line of proc.stdout) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const data = JSON.parse(trimmed) as JsonRpcResponse;
          if (data.result !== undefined) {
            yield data.result;
          } else if (data.error) {
            yield `[ERROR] ${data.error.message}`;
            break;
          }
        } catch {
          // Raw text output
          yield trimmed;
        }
      }
    } finally {
      clearTimeout(timeoutId);
      done = true;
      proc.stdin.end();
      proc.kill();
    }
  }

  /**
   * Send a single chat message.
   */
  async chat(message: string, timeout = 120): Promise<string> {
    return this.run(message, timeout);
  }
}

/**
 * Demo function demonstrating TypeScript SDK usage.
 */
export async function demo(): Promise<void> {
  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    console.log("⚠️  Set DEEPSEEK_API_KEY environment variable to run this demo");
    return;
  }

  const agent = new ReasonixAgent({
    projectPath: process.cwd(),
    model: "deepseek-flash",
    autoPlan: true,
  });

 console.log("🧠 DeepSeek-Reasonix TypeScript Demo");
  console.log("─".repeat(40));
  console.log("Agent initialized.\n");

  const task = "Write a simple REST API endpoint for user registration in Express.js";
  console.log(`You: ${task}`);
  console.log("Agent: ", end="");

  const response = await agent.run(task, 120);
  console.log(response);
}

// Run demo if executed directly
if (require.main === module) {
  demo().catch(console.error);
}