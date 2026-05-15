from datetime import datetime


def handle(args: str, ctx) -> str:
    topic = args.strip()
    if not topic:
        return "Need a topic. Try: /note <what the note is about>"

    # Build the full prompt: system voice + note template + memory context + the actual ask
    system_voice = ctx.prompts.system()
    note_template = ctx.prompts.load("note")
    memory = ctx.memory.all_context()

    full_system = f"{system_voice}\n\n{note_template}"
    if memory:
        full_system += f"\n\n# Adam's Current Context\n\n{memory}"

    today = datetime.now().strftime("%Y-%m-%d")
    user_prompt = f"Today's date is {today}.\n\nWrite an Obsidian note on this topic:\n\n{topic}"

    # Use the note-specific model from config (larger model for better quality)
    note_model = ctx.config.get("ollama", {}).get("note_model")

    try:
        content = ctx.ollama.generate(user_prompt, system=full_system, model=note_model)
    except Exception as e:
        return f"[error generating note] {e}"

    try:
        path = ctx.writer.write_note(topic, content)
    except Exception as e:
        return f"[error saving note] {e}"

    return f"Note saved to:\n{path}\n\nGo review it in Obsidian. In bocca al lupo."