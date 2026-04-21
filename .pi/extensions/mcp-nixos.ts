import { type Static, Type } from "@mariozechner/pi-ai";
import { defineTool, type ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const extensionDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(extensionDir, "../..");

const PYTHON_SCRIPT = String.raw`
import asyncio
import json
import os
import sys

from mcp_nixos.server import nix, nix_versions


def _callable(tool):
    # FastMCP 2.x wraps @mcp.tool() functions as FunctionTool (not directly callable);
    # FastMCP 3.x keeps them as plain async functions. Support both.
    return getattr(tool, "fn", tool)


async def main() -> None:
    tool = os.environ["PI_NIXOS_TOOL"]
    args = json.loads(os.environ["PI_NIXOS_ARGS"])

    if tool == "nix":
        result = await _callable(nix)(**args)
    elif tool == "nix_versions":
        result = await _callable(nix_versions)(**args)
    else:
        raise ValueError(f"Unknown tool: {tool}")

    sys.stdout.write(result)


asyncio.run(main())
`;

interface CommandResult {
	code: number | null;
	stdout: string;
	stderr: string;
}

class CancelledError extends Error {
	constructor() {
		super("Cancelled");
		this.name = "CancelledError";
	}
}

async function runCommand(
	command: string,
	args: string[],
	env: NodeJS.ProcessEnv,
	signal?: AbortSignal,
): Promise<CommandResult> {
	if (signal?.aborted) throw new CancelledError();

	return new Promise((resolvePromise, reject) => {
		const child = spawn(command, args, {
			cwd: projectRoot,
			env,
			stdio: ["ignore", "pipe", "pipe"],
		});

		let stdout = "";
		let stderr = "";

		child.stdout.on("data", (chunk) => {
			stdout += String(chunk);
		});
		child.stderr.on("data", (chunk) => {
			stderr += String(chunk);
		});

		const onAbort = () => {
			child.kill("SIGTERM");
			reject(new CancelledError());
		};
		if (signal) signal.addEventListener("abort", onAbort, { once: true });

		child.on("error", (err) => {
			signal?.removeEventListener("abort", onAbort);
			reject(err);
		});
		child.on("close", (code) => {
			signal?.removeEventListener("abort", onAbort);
			resolvePromise({ code, stdout, stderr });
		});
	});
}

async function runNixosTool(tool: "nix" | "nix_versions", args: unknown, signal?: AbortSignal): Promise<string> {
	const env: NodeJS.ProcessEnv = {
		...process.env,
		PI_NIXOS_TOOL: tool,
		PI_NIXOS_ARGS: JSON.stringify(args),
	};
	delete env.PYTHONPATH;
	delete env.PYTHONHOME;
	delete env.__PYVENV_LAUNCHER__;

	const candidates: Array<{ command: string; args: string[] }> = [];
	const venvPython = resolve(projectRoot, ".venv/bin/python");
	if (existsSync(venvPython)) {
		candidates.push({ command: venvPython, args: ["-c", PYTHON_SCRIPT] });
	}
	candidates.push(
		{ command: "uv", args: ["run", "python", "-c", PYTHON_SCRIPT] },
		{ command: "python3", args: ["-c", PYTHON_SCRIPT] },
		{ command: "python", args: ["-c", PYTHON_SCRIPT] },
	);

	const errors: string[] = [];
	for (const candidate of candidates) {
		try {
			const result = await runCommand(candidate.command, candidate.args, env, signal);
			if (result.code === 0) {
				return result.stdout.trimEnd();
			}
			errors.push(`${candidate.command} exited with ${result.code}: ${(result.stderr || result.stdout).trim()}`);
		} catch (error) {
			// Cancellation stops retries — don't spawn more Python processes after abort.
			if (error instanceof CancelledError || signal?.aborted) {
				throw error instanceof CancelledError ? error : new CancelledError();
			}
			const message = error instanceof Error ? error.message : String(error);
			errors.push(`${candidate.command}: ${message}`);
		}
	}

	throw new Error(
		[
			"Failed to run mcp-nixos from pi.",
			"Tried .venv/bin/python, uv, python3, and python in the repository root.",
			...errors,
		].join("\n"),
	);
}

const nixToolParams = Type.Object({
	action: Type.String({
		description:
			"One of: search, info, stats, browse, channels, flake-inputs, cache, store. " +
			"search = keyword lookup; info = details for a specific name; " +
			"browse = walk an option hierarchy by prefix (home-manager/darwin/nixvim/noogle only); " +
			"store = read files or list directories at an explicit /nix/store/ path.",
	}),
	query: Type.Optional(
		Type.String({
			description:
				"Search term for 'search', exact name for 'info', prefix path for 'browse'. " +
				"For flake-inputs: input_name or input:path. For store: absolute /nix/store/ path. " +
				"Omit for 'stats'/'channels'.",
		}),
	),
	source: Type.Optional(
		Type.String({
			description:
				"Data source for search/info/stats/browse/cache. One of: nixos (default), " +
				"home-manager, darwin, flakes, flakehub, nixvim, wiki, nix-dev, noogle, nixhub. " +
				"For action=flake-inputs, this may instead be a path to a flake directory; " +
				"omit/default to use the current project. Ignored by action=store.",
		}),
	),
	type: Type.Optional(
		Type.String({
			description:
				"Sub-type of query. For source=nixos with action=search, one of: " +
				"packages, options, programs, flakes. For source=nixos with action=info, one of: " +
				"package, option. For flake-inputs, one of: list, ls, read. For store, one of: " +
				"ls, read. Ignored by most other sources.",
		}),
	),
	channel: Type.Optional(
		Type.String({ description: "NixOS channel: unstable (default), stable, or a release like 25.05." }),
	),
	limit: Type.Optional(
		Type.Integer({ description: "Max results. 1-100 (or 1-2000 for flake-inputs/store read). Default 20." }),
	),
	version: Type.Optional(
		Type.String({ description: "Only used by action=cache. Package version (default: latest)." }),
	),
	system: Type.Optional(
		Type.String({
			description: "Only used by action=cache. System arch e.g. x86_64-linux. Empty for all.",
		}),
	),
});

type NixToolParams = Static<typeof nixToolParams>;

const nixToolDescription = [
	"Query live NixOS data (packages, options, flakes, wiki, nix.dev, Home Manager, nix-darwin, Nixvim, Noogle, NixHub, binary cache).",
	"",
	"Examples (copy the JSON shape exactly):",
	'  Search NixOS packages:    {"action": "search", "query": "firefox"}',
	'  Search NixOS options:     {"action": "search", "query": "nginx", "type": "options"}',
	'  Get a package:            {"action": "info", "query": "firefox"}',
	'  Get an option:            {"action": "info", "query": "services.nginx.enable", "type": "option"}',
	'  Search Home Manager:      {"action": "search", "query": "git", "source": "home-manager"}',
	'  Browse HM option tree:    {"action": "browse", "query": "programs", "source": "home-manager"}',
	'  Search the wiki:          {"action": "search", "query": "zfs", "source": "wiki"}',
	'  List channels:            {"action": "channels"}',
	'  Check binary cache:       {"action": "cache", "query": "firefox"}',
	'  List a store directory:   {"action": "store", "type": "ls", "query": "/nix/store/abc...-foo"}',
	'  Read a store file:        {"action": "store", "type": "read", "query": "/nix/store/abc...-foo/bin/foo"}',
	"",
	"Notes:",
	"  - To search NixOS options, use action=search with type=options. Do NOT use action=browse for source=nixos.",
	"  - action=browse walks a pre-indexed option tree and only supports home-manager, darwin, nixvim, or noogle.",
	"  - Omit optional parameters; don't pass empty strings.",
	"  - For package version history use the separate nix_versions tool.",
].join("\n");

const nixTool = defineTool({
	name: "nix",
	label: "NixOS",
	description: nixToolDescription,
	promptSnippet:
		"Prefer the nix tool over web search for NixOS packages, options, flakes, wiki, nix.dev, Home Manager, nix-darwin, Nixvim, Noogle, flake inputs, and binary cache status.",
	promptGuidelines: [
		"Prefer the nix tool over web search for NixOS-related package, option, flake, wiki, nix.dev, and cache questions.",
		'To search NixOS options: {"action": "search", "query": "<keyword>", "type": "options"}.',
		'To inspect a NixOS option: {"action": "info", "query": "<option.path>", "type": "option"}.',
		"action=browse is for walking option prefixes in home-manager, darwin, nixvim, or noogle only — never with source=nixos.",
	],
	parameters: nixToolParams,
	async execute(_toolCallId: string, params: NixToolParams, signal: AbortSignal | undefined) {
		// Legacy alias: older model sessions may still emit action=options.
		// server.py also normalizes this, but translating here keeps details.args honest.
		const action = params.action === "options" ? "browse" : params.action;

		// Only forward keys the caller actually set. Passing empty-string defaults would
		// (a) echo noisy args back in details.args, contradicting the "omit optional
		// parameters" guidance in the tool description, and (b) train small models to
		// copy those empties into future calls. The Python server already supplies its
		// own sensible defaults when a key is omitted.
		const normalized: Record<string, string | number> = { action };
		if (params.query !== undefined) normalized.query = params.query;
		if (params.source !== undefined) normalized.source = params.source;
		if (params.type !== undefined) normalized.type = params.type;
		if (params.channel !== undefined) normalized.channel = params.channel;
		if (params.limit !== undefined) normalized.limit = params.limit;
		if (params.version !== undefined) normalized.version = params.version;
		if (params.system !== undefined) normalized.system = params.system;

		const text = await runNixosTool("nix", normalized, signal);
		return {
			content: [{ type: "text", text }],
			details: { tool: "nix", args: normalized },
		};
	},
});

const nixVersionsParams = Type.Object({
	package: Type.String({ description: "Package name, e.g. git or firefox." }),
	version: Type.Optional(Type.String({ description: "Optional exact version to find." })),
	limit: Type.Optional(Type.Integer({ description: "How many recent versions to return (1-50, default 10)." })),
});

type NixVersionsParams = Static<typeof nixVersionsParams>;

const nixVersionsTool = defineTool({
	name: "nix_versions",
	label: "NixOS Versions",
	description: [
		"Get a Nix package's version history from NixHub.io (commit hashes, license, homepage, programs).",
		"",
		"Examples:",
		'  Recent versions:      {"package": "git"}',
		'  Find exact version:   {"package": "git", "version": "2.42.0"}',
	].join("\n"),
	promptSnippet: "Look up historical versions for a Nix package, including commit hashes and metadata.",
	promptGuidelines: [
		"Use nix_versions when the user wants version history or wants to pin a specific historical package version.",
	],
	parameters: nixVersionsParams,
	async execute(_toolCallId: string, params: NixVersionsParams, signal: AbortSignal | undefined) {
		const normalized: Record<string, string | number> = { package: params.package };
		if (params.version !== undefined) normalized.version = params.version;
		if (params.limit !== undefined) normalized.limit = params.limit;

		const text = await runNixosTool("nix_versions", normalized, signal);
		return {
			content: [{ type: "text", text }],
			details: { tool: "nix_versions", args: normalized },
		};
	},
});

export default function mcpNixosExtension(pi: ExtensionAPI) {
	pi.registerTool(nixTool);
	pi.registerTool(nixVersionsTool);
}
