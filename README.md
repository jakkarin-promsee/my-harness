# my-harness

A from-scratch agent harness for learning how coding agents work: the model loop, tools, permissions, context, prompts, sessions, and provider adapters are built here rather than hidden behind an agent SDK. It is a personal learning project and an independent harness with local and API model lanes.

**Start here for the whole picture.** This page shows what you can do, how to run it, and how the pieces fit together. [The Guidebook](docs/GUIDEBOOK.md) is the detailed index and manual for every control, extension point, and design note.

## See it in action

This short REPL walkthrough uses built-in controls; the values and session ID shown are examples:

```text
$ uv run harness
researcher-harness | provider: ollama | model: qwen3:4b-instruct | mode: build | agent: build | prompt: micro | voice: normal
you> /prompt
  * micro     backbone ~286 tokens
    compact   backbone ~602 tokens
    standard  backbone ~897 tokens
    full      backbone ~1,092 tokens

you> /think
  think: off (off|on|low|medium|high)

you> /tokens
  [context] ~732 tokens (9% of 8,192)

you> /agent plan
  agent: plan | mode: explore | model: qwen3:4b-instruct | session: …
```

The token figures vary with the prompt and environment. This example uses a configured 8,192-token window; the harness defaults to 4,096 when `OLLAMA_CONTEXT_LENGTH` is unset. `/prompt` changes the size of the system-prompt backbone; `/think` changes the provider's reasoning setting where supported; `/voice` changes narration; `/tokens` reports estimated context use; `/agent` changes role, prompt, and default permissions. The model can read and search files, ask questions, use a todo list, propose edits, run commands through the permission gate, and call configured MCP tools.

For a real task, a local model can inspect the repository through `read_file`:

```text
$ uv run harness --mode explore -p "Read README.md and report its first Markdown heading in one sentence."
  [tool] read_file -> [read_file] README.md - lines 1-20 …
agent> The first Markdown heading in README.md is "# researcher-harness".
The first Markdown heading in README.md is "# researcher-harness".
```

This abbreviated transcript shows the tool call and answer. Headless mode sends status and tool activity to stderr and the final answer to stdout; the exact wording depends on the model.

For a single noninteractive task, use headless mode:

```bash
uv run harness -p "Summarize the architecture of this repository."
uv run harness --agent plan -p "Inspect this change and propose a plan."
uv run harness --resume -p "Continue the previous task."
```

Headless mode prints the final answer to stdout and exits with success or failure; permission prompts cannot be answered there, so tools in the `ask` state are denied unless you pass `-y`. See [launch flags](docs/GUIDEBOOK.md#launch-flags) for the full behavior.

## Install and run

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/). Run these commands from the repository root; `uv run` installs the project and its dependencies as needed.

```bash
uv sync
uv run pytest -q
uv run harness --help
```

Choose a model lane:

| Command                       | Lane                                      | Setup                                                                                               |
| ----------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `uv run harness`              | Local Ollama, default `qwen3:4b-instruct` | Run Ollama and pull the model with `ollama pull qwen3:4b-instruct`.                                 |
| `uv run harness ollama-think` | Local thinking model, `qwen3:4b`          | Pull it with `ollama pull qwen3:4b`.                                                                |
| `uv run harness gemini`       | Gemini Flash Lite API                     | Set `GEMINI_API_KEY`.                                                                               |
| `uv run harness gemini-flash` | Gemini Flash API                          | Set `GEMINI_API_KEY`.                                                                               |
| `uv run harness anthropic`    | Anthropic API                             | Set `ANTHROPIC_API_KEY`; the adapter is implemented but has not passed a live test in this project. |

Put API keys in an untracked `.env` at the repository root or in your environment. Never commit `.env`. The selected provider makes its own model calls; Ollama stays local, while API lanes need network access and may incur charges. `OLLAMA_MODEL` overrides the default Ollama model, and `ANTHROPIC_MODEL` overrides the Anthropic model. To use a different local context window, set `OLLAMA_CONTEXT_LENGTH` before launching the harness and configure the Ollama server with the same window. The harness uses that value for its meter and automatic compaction; it does not resize the server's window. The default estimate is 4,096 tokens. [Context controls](docs/GUIDEBOOK.md#context-controls--what-each-knob-changes) covers the distinction.

The bundled `harness.toml` starts a DuckDuckGo MCP search server through `uvx` on launch; its first startup may need a download. This repository's sample MCP configuration contains a machine-specific certificate path, so adapt or disable that server on another machine. [The MCP setup guide](docs/GUIDEBOOK.md#mcp-servers--the-infinite-tool-bus) has the details.

## The controls you will use

| Goal                                 | Command or setting                       | What changes                                                                                                                                         |
| ------------------------------------ | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pick local or API model              | `uv run harness [provider]`              | Selects `ollama`, `ollama-think`, `gemini`, `gemini-flash`, or `anthropic` at launch; a role can pin a different model.                              |
| Choose what the agent may touch      | `--mode NAME` or `/mode NAME`            | `chat`, `explore`, `build`, and `auto` are permission profiles from `harness.toml`.                                                                  |
| Change the agent's job               | `--agent NAME` or `/agent NAME`          | Switches among `build`, `plan`, `chill`, `reviewer`, and any roles in `agents/`.                                                                     |
| Switch between conversation and work | `/chat` or `/work`                       | Shortcuts to the `chill` and `build` roles.                                                                                                          |
| Adjust the prompt footprint          | `/prompt micro\|compact\|standard\|full` | Changes the system-prompt tier and starts a new session file while retaining conversation history.                                                   |
| Adjust reasoning effort              | `/think off\|on\|low\|medium\|high`      | Requests a supported thinking setting from the active model; support varies by provider and model.                                                   |
| Adjust narration                     | `/voice quiet\|normal\|explain`          | Changes how much the agent talks while it works.                                                                                                     |
| Inspect or reduce context            | `/tokens` and `/compact`                 | Shows estimated context use, or summarizes and replaces older conversation content. Automatic compaction also runs at a provider-specific threshold. |
| Set the local context window         | `OLLAMA_CONTEXT_LENGTH` before launch    | Sets the harness's Ollama window estimate; configure the Ollama server to match. Defaults to 4,096.                                                  |
| Continue work                        | `--sessions` and `--resume [ID]`         | Lists or replays JSONL session journals.                                                                                                             |
| Run one task for a script            | `-p "TASK"`                              | Runs one turn and returns only the final answer on stdout.                                                                                           |
| Inspect external tools               | `/mcp`                                   | Lists connected MCP servers and their mounted tools.                                                                                                 |
| Reuse a prompt                       | `/NAME args`                             | Expands `commands/NAME.md`, substituting `{{args}}`.                                                                                                 |

There is no live `/context` command: `/tokens` measures current estimated use, `/compact` reduces conversation history, `/prompt` changes system-prompt size, and the Ollama window is configured before launch. Automatic compaction runs between interactive turns, not after a one-turn `-p` run. [The command reference](docs/GUIDEBOOK.md#built-in-slash-commands) explains the lifecycle and limits of each knob.

### Permission modes at a glance

| Mode      | Default behavior                                                                                                  |
| --------- | ----------------------------------------------------------------------------------------------------------------- |
| `chat`    | No tools are offered to the model.                                                                                |
| `explore` | Local reads are allowed; web fetching asks; writes and shell commands are denied.                                 |
| `build`   | Local reads are allowed; writes, shell commands, web fetching, and subagents ask.                                 |
| `auto`    | Reads and writes inside the working directory are allowed; shell commands, web fetching, and subagents still ask. |

`-y` approves an `ask` decision without prompting; it never overrides a `deny`. The active policy lives in [harness.toml](harness.toml), and the [Guidebook](docs/GUIDEBOOK.md#modes--how-much-can-it-touch) covers precedence and directory boundaries.

## How it works

The agent is a loop: it sends the current conversation and tool schemas to a model, executes any requested tools through the permission gate, appends their results, and calls the model again until it returns an answer.

```text
Human → CLI / REPL → Agent loop → provider adapter → model
                       ↓     ↑
                permission gate → tools / MCP
                       ↓
               messages, meter, session journal
```

### One request, step by step

1. The CLI loads the selected provider, active permission mode, and any saved session. It assembles the first system message from the tiered [`system.md`](src/harness/prompts/system.md) backbone, the active role, the working-directory environment and project map, `AGENTS.md`, and short descriptions of available skills.
2. The loop passes the conversation (`messages`) and JSON tool schemas to the provider adapter. The adapter translates that shared format to the selected model's API and translates the reply back; the model sees tool names, descriptions, and argument schemas, not Python functions or direct machine access. In `chat` mode, the CLI sends no tool schemas.
3. A reply can contain final text or `tool_calls` with an ID, tool name, and JSON arguments. The loop appends the assistant reply to `messages`, decodes each call, checks the active permission policy, looks up the Python function in the registry, and executes approved calls.
4. Every call produces a string result. The loop appends it as a `role: tool` message with the matching `tool_call_id`, so the next model call can connect the observation to its request. Unknown tools, invalid arguments, denied calls, and tool errors become readable result text that the model can react to.
5. The loop calls the model again with the updated history until it returns final text or reaches a safety stop. A callback journals each new message to `sessions/*.jsonl` immediately; other callbacks stream text, show tool activity, and update the token meter.

The exchange below is **shape only**; real provider wire formats differ, and the adapters handle that translation:

```text
user: "What does this file do?"
assistant.tool_calls: [{ id: "call_1", name: "read_file", arguments: { path: "src/harness/core/loop.py" } }]
tool: { tool_call_id: "call_1", content: "[read_file] src/harness/core/loop.py - lines 1-20 of ..." }
assistant: "This is the agent loop..."
```

### Tools available to the agent

| Tool                       | What the agent gets back                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `list_dir`, `glob`, `grep` | A bounded map of directory entries, matching paths, or text hits; search skips noisy folders such as `.git` and `.venv`.                   |
| `read_file`                | A line-numbered, pageable excerpt with a header and a hint for reading the next page.                                                      |
| `write_file`, `edit_file`  | A write receipt or an exact-string replacement receipt; `edit_file` refuses missing or repeated matches, and approval prompts show a diff. |
| `run_shell`                | Exit code plus stdout and stderr, with a 60-second command timeout.                                                                        |
| `web_fetch`                | Readable text extracted from a fetched page; network access goes through the permission gate.                                              |
| `todo_write`               | An external task list the model can update and revisit instead of relying on conversation memory alone.                                    |
| `ask_user`                 | The human's answer as a tool result in the same agent turn; a scripted run can use a flagged recommended default.                          |
| `spawn_subagent`           | A child loop's final answer; `fresh` starts with a clean prompt and `fork` copies the parent conversation.                                 |
| `mcp__server__tool`        | A result from a configured MCP server, mounted into the same registry and permission system as built-in tools.                             |

The model can request these tools only when its mode advertises them, and every requested call still passes the active policy. `build` asks before writes, shell commands, web fetches, and subagents; `auto` allows writes inside the working directory but still asks for shell and network actions; `explore` allows local inspection and asks before a web fetch. `-y` upgrades `ask`, never `deny`. See the [full tool map](src/harness/tools/README.md) and [permission design](docs/GUIDEBOOK.md#modes--how-much-can-it-touch).

### How context stays usable

Tool output is framed with what happened, then capped before it enters the next model call; long results keep both the beginning and end so a trailing error is not lost. Provider reasoning can be shown in the terminal but is stripped from conversation history. Subagents keep their own transcripts, returning only their final text to the parent. `/tokens` estimates current window use, while `/compact` summarizes and replaces older messages when the conversation grows too large; the original JSONL session remains on disk. [Context controls](docs/GUIDEBOOK.md#context-controls--what-each-knob-changes) and [sessions](docs/GUIDEBOOK.md#sessions-tokens-and-the-meter) explain the exact behavior.

### Where each part lives

| Part                     | What it does                                                                                                        | Start reading                                               |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| CLI and REPL             | Parses launch flags, runs slash commands, streams output, chooses providers, and wires the components together.     | [`src/harness/cli/repl.py`](src/harness/cli/repl.py)        |
| Agent loop               | Calls the model, dispatches tool requests, handles interrupted or empty turns, and returns the final answer.        | [`src/harness/core/loop.py`](src/harness/core/loop.py)      |
| Provider adapters        | Translate the shared message and tool format to native Ollama, Gemini's OpenAI-compatible API, or native Anthropic. | [`src/harness/providers/`](src/harness/providers/README.md) |
| Tool registry            | Provides file operations, search, shell, web fetch, todo, human questions, and MCP tools.                           | [`src/harness/tools/`](src/harness/tools/README.md)         |
| Context and roles        | Assembles the tiered backbone, active role, project memory, skill descriptions, and environment map.                | [`src/harness/core/`](src/harness/core/README.md)           |
| Permissions and sessions | Gates each tool call; journals messages to JSONL for resume and compaction.                                         | [`src/harness/core/`](src/harness/core/README.md)           |

The loop receives its model, tools, permission decision, and output callbacks as inputs, so the same code runs against a `FakeModel` in the offline tests without making API calls.

## Extend it

Most customization is a file or a config entry: add a role in [`agents/`](agents/README.md), a reusable slash command in [`commands/`](commands/README.md), a model-facing procedure in [`skills/`](skills/README.md), or an MCP server and permission rule in [`harness.toml`](harness.toml). New Python tools and providers live under `src/harness/`. [The extension recipes](docs/GUIDEBOOK.md#recipes) walk through each path and its verification step.

## Project status and deeper reading

The packaged harness is release 1. The Stage 0–2 learning work, Stage 2C cognitive core, and MCP client are implemented; [ROADMAP4](docs/ROADMAP4.md) tracks the subsequent ability and agency work, while [problem.md](docs/problem.md) tracks open decisions and live-test limitations. Historical benchmark counts and dated claims belong in the [roadmaps](docs/ROADMAP.md) and [design notes](docs/notes/README.md), where their test conditions are recorded.

| If you want to…                              | Read                                                              |
| -------------------------------------------- | ----------------------------------------------------------------- |
| Find a command, setting, or extension recipe | [The Guidebook](docs/GUIDEBOOK.md)                                |
| Understand why a feature was built this way  | [Design-note index](docs/notes/README.md)                         |
| Inspect the current plan and unfinished work | [ROADMAP4](docs/ROADMAP4.md) and [open problems](docs/problem.md) |
| Run the offline or live validation suites    | [Tests](tests/README.md) and [acceptance](acceptance/README.md)   |
| See the frozen first-stage learning artifact | [`archive/mvp/`](archive/mvp/)                                    |

## License

Original code and documentation authored by Jakkarin Promsee are licensed under the [MIT License](LICENSE). Third-party code, assets, datasets, and other materials are not covered by this license; their original terms apply.
