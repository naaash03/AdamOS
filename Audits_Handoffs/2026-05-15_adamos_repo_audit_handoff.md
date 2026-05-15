# AdamOS Repo Audit and Handoff

Date: 2026-05-15

Repo path: `C:\Users\imada\Code\adamos`

Branch: `main`

Latest commit observed: `3c96038 AdamOS v0: working popup, Ollama integration, help command, hotkey`

Validation run during audit: `python -m compileall main.py adamos handlers` passed.

## Executive Summary

AdamOS is currently a small local Python desktop assistant. It opens a CustomTkinter window, accepts text input, routes slash commands, and sends free-form chat to a local Ollama model. The assistant is designed around Adam Nash's personal voice/context, with an Obsidian writing path and a lightweight memory directory.

The committed baseline appears to be "v0": popup UI, Ollama integration, `/help`, and a global hotkey. The working tree now has in-progress additions for prompt loading and `/note` generation. Those changes are not committed yet.

The app is not a multi-agent platform yet. It is currently a local UI plus router plus handler system. The shape is good for incremental growth: add one handler at a time, wire it into `Router.routes`, give it prompt templates if needed, and keep writes constrained through safety helpers.

## Current Git State

`git status --short --branch` showed:

```text
## main...origin/main
 M adamos/router.py
 M main.py
?? adamos/prompt_loader.py
?? handlers/note.py
?? prompts/
```

Interpretation:

- `main.py` has been modified to add `PromptLoader` into the runtime context.
- `adamos/router.py` has been modified to register `/note` and to use the full system prompt plus memory for free chat.
- `adamos/prompt_loader.py` is new and untracked.
- `handlers/note.py` is new and untracked.
- `prompts/system.md` and `prompts/note.md` are new and untracked.

No committed test suite exists in the repo at the time of this audit.

## Repository Layout

```text
.
|-- main.py
|-- config.example.yaml
|-- config.yaml              # local only, gitignored
|-- requirements.txt
|-- adamos/
|   |-- __init__.py
|   |-- memory.py
|   |-- obsidian_writer.py
|   |-- ollama_client.py
|   |-- prompt_loader.py      # new, untracked
|   |-- router.py
|   |-- safety.py
|   `-- ui.py
|-- handlers/
|   |-- __init__.py
|   |-- help.py
|   `-- note.py              # new, untracked
|-- prompts/
|   |-- system.md             # new, untracked
|   `-- note.md               # new, untracked
`-- Audits_Handoffs/
    `-- 2026-05-15_adamos_repo_audit_handoff.md
```

## Runtime Architecture

The runtime flow is:

1. `main.py` loads `config.yaml`.
2. `main.py` builds a `SimpleNamespace` context object with shared services:
   - `config`
   - `ollama`
   - `writer`
   - `memory`
   - `prompts`
3. `main.py` creates `Router(ctx)`.
4. `main.py` creates `AdamOSWindow(router)`.
5. `keyboard.add_hotkey()` registers the configured global hotkey.
6. The CustomTkinter main loop starts.
7. User submits text through the UI.
8. UI calls `router.dispatch(text)` in a background thread.
9. Router either:
   - dispatches slash commands to a handler, or
   - sends free text to Ollama with the system prompt and memory context.
10. UI writes the response back into the textbox.

This is a straightforward command-router architecture. The shared `ctx` object is the dependency injection mechanism. It keeps handlers simple because they receive `args` plus `ctx`, but it also means handler dependencies are implicit rather than typed.

## Configuration

`config.example.yaml` contains:

```yaml
paths:
  obsidian_vault: "C:/Users/imada/Desktop/Grad School Knowledge Base"
  agent_inbox: "C:/Users/imada/Desktop/Grad School Knowledge Base/06 Agent Inbox"
  memory: "G:/My Drive/AdamOS/memory"
  logs: "G:/My Drive/AdamOS/logs"

ollama:
  host: "http://localhost:11434"
  default_model: "llama3.1:8b"
  code_model: "qwen2.5-coder:7b"

hotkey: "ctrl+alt+a"
```

Local `config.yaml` differs in one important way:

```yaml
agent_inbox: "C:/Users/imada/Desktop/Grad School Knowledge Base/00 Inbox"
```

That means generated notes currently go to `00 Inbox`, not `06 Agent Inbox`.

`config.yaml` is correctly ignored by `.gitignore`, so local path preferences are not meant to be committed.

## Dependencies

`requirements.txt` pins:

- `customtkinter`
- `keyboard`
- `PyYAML`
- `requests`
- `pyperclip`
- support dependencies such as `certifi`, `urllib3`, `packaging`, etc.

Important note: `pyperclip` is installed but no current code imports or uses it. The help text advertises a `/claude` command that would copy a prompt to the clipboard, so `pyperclip` is probably reserved for that planned feature.

## Main Entry Point: `main.py`

`main.py` is the composition root.

Current responsibilities:

- Load `config.yaml` using `yaml.safe_load`.
- Exit with a clear message if `config.yaml` is missing.
- Create:
  - `OllamaClient`
  - `ObsidianWriter`
  - `Memory`
  - `PromptLoader`
  - `Router`
  - `AdamOSWindow`
- Register the global hotkey from config, defaulting to `ctrl+alt+a`.
- Start the UI loop.

Notable behavior:

- If hotkey registration fails, the app prints a warning and continues. This is good because the `keyboard` package can require elevated privileges on some systems.
- The app assumes config keys exist. Missing `paths.agent_inbox`, `paths.memory`, `ollama.host`, or `ollama.default_model` will raise a `KeyError`.
- No logging is currently implemented even though config has a `logs` path.

## UI Layer: `adamos/ui.py`

`AdamOSWindow` owns the desktop window.

Current behavior:

- Uses CustomTkinter dark mode and blue theme.
- Creates a 700x500 topmost window.
- Displays an output textbox and an entry field.
- Submits on Enter.
- Adds user text and a temporary `...` line.
- Runs router dispatch in a daemon background thread.
- Writes the response back onto the Tkinter main thread using `root.after`.

Important implementation detail:

- `_replace_thinking()` deletes `"end-2l"` to `"end-1l"` to remove the temporary `...` line. This is a simple approach and works for the current UI, but it is fragile if output formatting changes or if multiple requests overlap.

Potential issue:

- There is no disabled state while a request is running. A user can submit multiple prompts rapidly, starting multiple background threads. Responses could arrive out of order and the `...` deletion could remove the wrong line.

Recommended future improvement:

- Track each pending request explicitly or disable input while one request is running.
- Consider a message model instead of editing raw textbox line positions.

## Router: `adamos/router.py`

`Router` is the central command dispatcher.

Current routes:

```python
self.routes = {
    "help": help_handler.handle,
    "note": note_handler.handle,
}
```

Slash command behavior:

- Trims input.
- If input starts with `/`, split the first token into `cmd`.
- Looks up `cmd` in `self.routes`.
- Calls handler as `handler(args, self.ctx)`.
- Returns an unknown-command message if no route exists.

Free chat behavior:

- Loads the base system prompt using `self.ctx.prompts.system()`.
- Loads memory context using `self.ctx.memory.all_context()`.
- Appends memory under `# Memory Context` if present.
- Calls `self.ctx.ollama.generate(text, system=full_system)`.

Important current mismatch:

- `handlers/help.py` advertises `/claude`, `/briefing`, and `/ask`.
- `Router.routes` only supports `/help` and `/note`.
- Free-form text already behaves like `/ask`, but `/ask` itself is not implemented.

Recommended future fixes:

- Either implement `/ask`, `/briefing`, and `/claude`, or remove them from help text until they exist.
- Add a route registration pattern if commands grow past a handful.
- Add handler-level error boundaries if some commands should fail gracefully without relying on the UI catch-all.

## Prompt Loading: `adamos/prompt_loader.py`

`PromptLoader` is a new untracked file.

Current behavior:

- Defaults to loading prompt files from `prompts/`.
- `load(name)` reads `prompts/{name}.md`.
- `system()` is a convenience method for `load("system")`.

Risks:

- Missing prompt files raise `FileNotFoundError`.
- Router free chat now depends on `prompts/system.md`. If prompts are not present or the working directory is not repo root, free chat fails.
- `PromptLoader()` uses a relative path. Running the app from a different current working directory will break prompt loading.

Recommended future improvement:

- Anchor the default prompt path to the repository or package location, for example relative to `Path(__file__).resolve().parents[1]`.
- Optionally make `prompts_dir` configurable in `config.yaml`.

## Ollama Client: `adamos/ollama_client.py`

`OllamaClient` wraps Ollama's `/api/generate`.

Current behavior:

- Strips trailing slash from host.
- Uses default model unless a model override is passed.
- Sends:
  - `model`
  - `prompt`
  - `system`
  - `stream: False`
- Timeout is 180 seconds.
- Raises HTTP errors via `r.raise_for_status()`.
- Returns `r.json()["response"].strip()`.

Risks:

- Assumes Ollama is running and reachable.
- Assumes response JSON has a `response` key.
- No custom error messages for connection failure, timeout, missing model, or malformed response.
- No streaming, so the UI stays in a thinking state until the full response is complete.

Recommended future improvement:

- Wrap `requests` exceptions with user-friendly messages.
- Consider a health check command.
- Eventually add streaming support if the UI is meant to feel more alive.

## Memory: `adamos/memory.py`

`Memory` represents a directory of markdown files used as context.

Current behavior:

- Creates the memory directory if missing.
- `load(name)` reads `{memory_dir}/{name}.md`, returning an empty string if absent.
- `all_context()` loads these files in fixed order:
  - `profile.md`
  - `projects.md`
  - `rules.md`
- Non-empty files are joined as markdown sections.

Strengths:

- Simple and predictable.
- Good initial abstraction for personal context.

Risks:

- There is no size control. If memory files grow large, prompts may become too big for the local model.
- Memory is read wholesale on every free chat and note request.
- No error handling for inaccessible drives. The configured memory path is on `G:/My Drive/...`, which may fail if Google Drive is unavailable.

Recommended future improvement:

- Add a max character budget or summarization layer.
- Add a `/memory` or diagnostic command that reports which memory files are loaded.
- Fail softly if memory path is unavailable.

## Obsidian Writer: `adamos/obsidian_writer.py`

`ObsidianWriter` handles note file creation.

Current behavior:

- Takes an `agent_inbox` path.
- Creates that directory if missing.
- Sanitizes note title into a filename by allowing alphanumeric characters, spaces, hyphens, and underscores.
- Writes `{safe_title}.md`.
- If a file exists, appends a timestamp like `YYYYMMDD-HHMMSS`.
- Calls `assert_within(path, self.inbox)` before writing.

Strengths:

- The writer has a safety boundary to prevent writes outside the inbox.
- Duplicate filenames are handled.

Potential issue:

- Safety is checked before the duplicate timestamp branch, not after it. The timestamp path is also built under `self.inbox`, so it is practically safe, but the cleanest version would call `assert_within()` after final path selection too.

Recommended future improvement:

- Re-run `assert_within()` after timestamp fallback.
- Consider trimming extremely long titles to avoid filesystem path length problems.
- Consider returning both path and title metadata if the UI needs richer responses.

## Safety: `adamos/safety.py`

`assert_within(path, allowed_root)` resolves both paths and checks that the target path is inside the allowed root.

This is a good foundational helper for any future file-writing commands. Future destructive or filesystem-writing handlers should use this same pattern.

## Help Handler: `handlers/help.py`

`/help` returns static text.

Current advertised commands:

```text
/help
/note <topic>
/claude <task>
/briefing
/ask <question>
```

Only `/help` and `/note` are implemented in the router today.

Recommendation:

- Update help text immediately to reflect actual commands, or implement the advertised routes.
- If this app is used daily, stale help text will cause confusion fast.

## Note Handler: `handlers/note.py`

`/note` is a new untracked handler.

Current behavior:

1. Accepts the rest of the command as `topic`.
2. If topic is empty, returns a usage message.
3. Loads:
   - system voice prompt from `prompts/system.md`
   - note template from `prompts/note.md`
   - memory context from `ctx.memory.all_context()`
4. Builds a combined system prompt:
   - system voice
   - note generation rules
   - optional memory context under `# Adam's Current Context`
5. Adds today's date to the user prompt.
6. Calls Ollama to generate note content.
7. Writes note content to Obsidian inbox with `ctx.writer.write_note(topic, content)`.
8. Returns the saved path.

Strengths:

- It keeps note-specific instructions in a prompt file instead of hardcoding them.
- It catches generation and save errors separately.
- It uses the topic as the filename, letting the writer sanitize it.

Risks:

- It trusts the model to produce valid Obsidian frontmatter.
- It does not validate that the returned note starts with frontmatter.
- It does not validate that the generated frontmatter `date` matches today's date.
- It does not post-process or repair forbidden style issues from the prompt, such as first-person voice or em dashes.
- The success message includes "In bocca al lupo." This is aligned with the system prompt style, but if strict app responses are desired, that could be moved into the prompt layer or removed.

Recommended future improvement:

- Add lightweight validation before saving:
  - starts with `---`
  - contains `title:`
  - contains `date: YYYY-MM-DD`
  - contains a top-level H1
- If validation fails, either retry once or save with a warning.
- Consider adding a `slugify_title()` helper that can be tested separately.

## Prompts

### `prompts/system.md`

This is the main AdamOS personality and operating contract.

It establishes:

- AdamOS is Adam Nash's personal assistant, not a generic chatbot.
- The desired voice is direct, Brooklyn/Italian-American, with a Bourdain/Soprano-inspired flavor but not caricature.
- It should be concise, honest, non-corporate, and willing to disagree.
- It should help with grad school, projects, Obsidian notes, prompts for other models, and eventually workouts/music/stocks/language learning.
- It must not take destructive actions, send emails, or delete things.
- It should acknowledge limitations because it is running on a small local model.

This file is now important to both free chat and `/note`. Any future handler can reuse it, but task-specific prompts should stay separate.

### `prompts/note.md`

This is the note-generation contract for `/note`.

It requires:

- Obsidian markdown output only.
- YAML frontmatter at the top.
- Fields:
  - `title`
  - `date`
  - `tags`
  - `status: draft`
  - `source: AdamOS`
  - `related: []`
- H1 title matching the topic.
- Useful sections organized around the topic.
- Optional Open Questions section only when warranted.
- No first-person writing as Adam.
- Minimal stylized voice.
- No invented facts.
- No em dashes.
- Length matched to the topic.

This is the strongest part of the new `/note` implementation. It gives the local model a clear product spec.

## Current Behavior by Command

### `/help`

Works. Returns static help text.

Issue: Help text includes commands that do not work yet.

### `/note <topic>`

Implemented in the dirty worktree, not committed.

Expected behavior: generates an Obsidian note using Ollama, then writes it into `paths.agent_inbox`.

Dependencies:

- Ollama must be running.
- Configured model must be installed in Ollama.
- `config.yaml` must exist.
- `prompts/system.md` and `prompts/note.md` must exist.
- Obsidian inbox path must be writable.
- Memory path should be readable, though missing memory files are tolerated.

### `/ask <question>`

Advertised but not implemented as a slash command.

Equivalent behavior is available by typing free-form text without a slash.

### `/claude <task>`

Advertised but not implemented.

Likely intended behavior: generate a detailed prompt for Claude/Codex and copy it to clipboard using `pyperclip`.

### `/briefing`

Advertised but not implemented.

Likely intended behavior: use memory files to produce a morning briefing.

## Free Chat Behavior

Typing anything without a slash now calls Ollama with:

- user text as the prompt
- `prompts/system.md` as the system prompt
- memory context appended if available

This is a major improvement over the committed baseline, which used a short hardcoded system string:

```python
"You are AdamOS, Adam's local assistant. Be concise and direct."
```

The new behavior gives free chat the real AdamOS voice and context.

## Known Gaps and Risks

### 1. Help Text Is Ahead of Implementation

The UI says `/claude`, `/briefing`, and `/ask` exist. They do not exist in `Router.routes`.

Impact: user confusion.

Fix: either implement those handlers or remove them from help text temporarily.

### 2. Prompt Directory Is Relative to Current Working Directory

`PromptLoader()` defaults to `Path("prompts")`.

Impact: app works when launched from repo root, but may fail if launched from another directory, a shortcut, Task Scheduler, or a packaged executable.

Fix: anchor prompt path relative to the project root or pass it from config.

### 3. No Tests

There are no unit tests or integration tests.

Minimum valuable tests:

- `Router.dispatch()` routes known commands.
- Unknown slash command returns expected message.
- Free chat passes system prompt and memory into Ollama.
- `PromptLoader.load()` loads prompts and fails clearly.
- `ObsidianWriter.write_note()` sanitizes filenames and prevents outside writes.
- `/note` handles empty topic, generation error, and save error.

### 4. UI Can Race Multiple Requests

Every Enter press starts a new daemon thread. The textbox thinking-line replacement assumes one active request.

Impact: out-of-order responses or wrong text deletion under rapid submission.

Fix: disable input during active request, queue requests, or track per-message placeholders.

### 5. Ollama Errors Are Raw

Most commands that call Ollama will surface raw request exceptions unless handlers catch them.

Impact: unpleasant UX when Ollama is not running or model is missing.

Fix: wrap `OllamaClient.generate()` exceptions into clearer app-level messages.

### 6. Memory Has No Budget

Memory files are included wholesale.

Impact: long memory files can degrade output, exceed context, or slow local generation.

Fix: budget memory by characters/tokens or add a summarization/indexing layer later.

### 7. No Logging Yet

Config contains `paths.logs`, but no logging code writes to it.

Impact: hard to debug failures after the fact.

Fix: add a minimal rotating log or append-only daily log for commands, exceptions, and generated file paths. Avoid logging sensitive full prompts unless explicitly desired.

### 8. Local Config Is Required

The app exits if `config.yaml` is missing.

Impact: first-run setup is manual.

Fix: add a setup command or copy from `config.example.yaml` with prompts.

## Suggested Next Build Order

1. Commit the current `/note` and prompt-loader work once reviewed.
2. Fix `PromptLoader` path anchoring so prompts load reliably outside repo root.
3. Make `/help` truthful by either removing planned commands or implementing stubs that say "not built yet."
4. Add a tiny test suite around router, writer, prompt loader, and note handler.
5. Add `/ask` as an explicit alias for free chat if help continues to advertise it.
6. Add `/claude` prompt-generation handler using a dedicated prompt file and `pyperclip`.
7. Add `/briefing` using memory files and a dedicated briefing prompt.
8. Add better Ollama error messages and an `/status` or `/doctor` command.
9. Add basic logging to `paths.logs`.
10. Improve UI request handling so concurrent submissions cannot corrupt output.

## Recommended Immediate Code Changes

These are small, high-value changes for the next chat:

### A. Anchor PromptLoader Paths

Current:

```python
def __init__(self, prompts_dir: str = "prompts"):
    self.dir = Path(prompts_dir)
```

Better:

```python
def __init__(self, prompts_dir: str | None = None):
    if prompts_dir is None:
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
    self.dir = Path(prompts_dir)
```

### B. Make Help Text Accurate

Short-term:

```text
/help
/note <topic>
```

Or mark planned commands explicitly:

```text
Planned, not built yet:
/claude
/briefing
/ask
```

### C. Add `/ask`

Since free chat already works, `/ask` can just call the same code path. The clean way is to extract `Router.chat(text)` and reuse it:

```python
def chat(self, text: str) -> str:
    system = self.ctx.prompts.system()
    memory = self.ctx.memory.all_context()
    full_system = f"{system}\n\n# Memory Context\n\n{memory}" if memory else system
    return self.ctx.ollama.generate(text, system=full_system)
```

Then `dispatch()` can call `self.chat(text)` for free chat, and an `ask` handler or router branch can call `self.chat(args)`.

### D. Validate Notes Before Saving

Add a minimal guard in `/note`:

- If generated content does not start with `---`, return an error or retry.
- If no H1 is present, return an error or retry.

This prevents bad model output from quietly becoming permanent notes.

## Mental Model for the Next Chat

Treat AdamOS as an early local assistant shell with these layers:

- `main.py`: bootstraps config and services.
- `ui.py`: desktop input/output.
- `router.py`: command dispatch and free-chat path.
- `handlers/`: one file per slash command.
- `prompts/`: markdown prompt contracts for assistant voice and task-specific behavior.
- `memory.py`: reads personal context markdown.
- `ollama_client.py`: local model boundary.
- `obsidian_writer.py`: controlled file-writing boundary.
- `safety.py`: path safety helpers.

The intended development style should be incremental:

1. Add one capability as a handler.
2. Give it a dedicated prompt file if it needs nontrivial model behavior.
3. Keep filesystem writes behind a small writer/helper with `assert_within`.
4. Add a focused test for routing and the handler.
5. Update `/help` only when the command actually works.

## Handoff Prompt for Main Chat Brain

Use this if feeding the project to another assistant:

```text
You are continuing development on AdamOS, a local Python desktop assistant in C:\Users\imada\Code\adamos.

The app uses CustomTkinter for a desktop window, `keyboard` for a global hotkey, Ollama for local generation, and Obsidian markdown files as an output target. `main.py` loads `config.yaml`, builds a context object with `OllamaClient`, `ObsidianWriter`, `Memory`, and `PromptLoader`, then starts `AdamOSWindow`.

The router lives in `adamos/router.py`. Slash commands are mapped in `Router.routes`; free-form text goes to Ollama. The current dirty worktree adds prompt loading and `/note`:

- `main.py` imports and injects `PromptLoader`.
- `adamos/router.py` registers `/note` and uses `prompts/system.md` plus memory for free chat.
- `adamos/prompt_loader.py` loads markdown prompts from `prompts/`.
- `handlers/note.py` generates an Obsidian note from a topic and saves it through `ObsidianWriter`.
- `prompts/system.md` defines AdamOS voice and operating rules.
- `prompts/note.md` defines the Obsidian note output contract.

Known issues to handle soon:

- `/help` advertises `/claude`, `/briefing`, and `/ask`, but only `/help` and `/note` are routed.
- `PromptLoader` uses a relative `prompts` path, so it may fail if the app is launched outside repo root.
- There are no tests.
- The UI can start concurrent request threads and may replace the wrong `...` line.
- Ollama errors are not user-friendly yet.
- Memory files are included wholesale with no prompt budget.

Do not rewrite the architecture. Keep the simple router/handler pattern. Make small, tested additions. Prioritize truthful help text, robust prompt path loading, `/ask` as an alias for free chat, and tests around router/writer/prompt loading.
```

## Final Audit Notes

The project is coherent and at the right level of simplicity for v0. The next risk is not architecture, it is capability drift: help text, prompts, and actual handlers need to stay synchronized. The other near-term risk is launch fragility from relative paths and local environment assumptions.

The best next move is to stabilize what already exists before adding more commands: commit or cleanly finish the `/note` work, make prompt loading path-safe, make help text truthful, and add a small test suite. After that, `/claude` and `/briefing` can be added without turning the codebase into a mess.
