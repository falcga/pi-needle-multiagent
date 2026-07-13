
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execFile } from "node:child_process";
import { join } from "node:path";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "call_junior_llm",
    label: "Call Junior LLM",
    description: "Delegates a task to a local small LLM (e.g., Qwen via Ollama) for tool call prediction.",
    parameters: Type.Object({
      query: Type.String({ description: "The natural language query for the junior LLM." }),
      tools: Type.String({ description: "A JSON string representing a list of available tools (OpenAPI spec)." }),
      modelName: Type.Optional(Type.String({ description: "The name of the LLM model to use via Ollama (e.g., 'qwen:0.5b'). Defaults to 'qwen:0.5b'."})),
      maxGenLen: Type.Optional(Type.Number({ description: "Maximum generation length (default: 512)." })),
      temperature: Type.Optional(Type.Number({ description: "Sampling temperature for generation (default: 0.7)." })),
      numPredict: Type.Optional(Type.Number({ description: "Number of tokens to predict. -1 for default (default: -1)." })),
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const pythonScriptPath = join(ctx.cwd, "needle_runner.py");
      const pythonExecutable = "python3"; // Or "python" depending on your system

      // Use provided modelName or default to 'qwen:0.5b'
      const modelToUse = params.modelName || "qwen:0.5b";

      const args = [
        pythonScriptPath,
        "--query", params.query,
        "--tools", params.tools,
        "--model-name", modelToUse,
      ];

      // Add optional parameters if they are provided
      if (params.maxGenLen !== undefined) {
        args.push("--max-tokens", params.maxGenLen.toString());
      }
      if (params.temperature !== undefined) {
        args.push("--temperature", params.temperature.toString());
      }
      if (params.numPredict !== undefined) {
        args.push("--num-predict", params.numPredict.toString());
      }

      return new Promise((resolve) => {
        execFile(pythonExecutable, args, { cwd: ctx.cwd, signal }, (error, stdout, stderr) => {
          if (error) {
            console.error(`Error executing needle_runner.py: ${stderr}`);
            resolve({
              content: [{ type: "text", text: `Error calling junior LLM: ${stderr}` }],
              isError: true,
              details: { error: error.message, stderr: stderr },
            });
            return;
          }

          try {
            const prediction = JSON.parse(stdout);
            resolve({
              content: [{ type: "json", json: prediction }],
              details: { stdout: stdout.trim(), stderr: stderr.trim() },
            });
          } catch (parseError: any) {
            console.error(`Error parsing JSON from needle_runner.py: ${parseError.message}\nSTDOUT: ${stdout}\nSTDERR: ${stderr}`);
            resolve({
              content: [{ type: "text", text: `Error parsing junior LLM output: ${parseError.message}` }],
              isError: true,
              details: { error: parseError.message, stdout: stdout.trim(), stderr: stderr.trim() },
            });
          }
        });
      });
    },
  });
}
