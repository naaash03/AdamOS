from datetime import datetime
from pathlib import Path


def _recent_inbox_files(inbox_path: str, days: int = 7) -> list[str]:
    """Return titles of files modified in the last `days` days in the inbox."""
    inbox = Path(inbox_path)
    if not inbox.exists():
        return []

    now = datetime.now().timestamp()
    cutoff = now - (days * 86400)

    recent = []
    for f in inbox.glob("*.md"):
        try:
            if f.stat().st_mtime >= cutoff:
                mod_date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
                recent.append(f"{mod_date} — {f.stem}")
        except OSError:
            continue

    # Sort newest first
    recent.sort(reverse=True)
    return recent


def handle(args: str, ctx) -> str:
    # Build the full prompt: system voice + briefing template + memory context
    system_voice = ctx.prompts.system()
    template = ctx.prompts.load("briefing")
    memory = ctx.memory.all_context()

    full_system = f"{system_voice}\n\n{template}"
    if memory:
        full_system += f"\n\n# Adam's Current Context\n\n{memory}"

    # Gather recent inbox activity
    inbox_path = ctx.config["paths"]["agent_inbox"]
    recent = _recent_inbox_files(inbox_path, days=7)
    if recent:
        recent_block = "\n".join(f"- {r}" for r in recent)
    else:
        recent_block = "(no files in inbox in the last 7 days)"

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    day_str = now.strftime("%A, %B %d, %Y")

    user_prompt = (
        f"Today is {day_str} ({today_str}).\n\n"
        f"Recent files in Adam's Obsidian inbox (last 7 days):\n{recent_block}\n\n"
        f"Generate the morning briefing."
    )

    note_model = ctx.config.get("ollama", {}).get("note_model")

    try:
        content = ctx.ollama.generate(user_prompt, system=full_system, model=note_model)
    except Exception as e:
        return f"[error generating briefing] {e}"

    # Save the briefing as a note for archival
    title = f"Morning Briefing {today_str}"
    try:
        path = ctx.writer.write_note(title, content)
    except Exception as e:
        # Still return content even if save fails
        return f"[briefing saved failed, here it is anyway]\n\n{content}\n\nSave error: {e}"

    # Return both the saved path and the briefing content itself
    return f"Briefing saved to:\n{path}\n\n---\n\n{content}"