import pyperclip


def handle(args: str, ctx) -> str:
    task = args.strip()
    if not task:
        return "Need a task. Try: /claude <what you want a prompt for>"

    # Build the full prompt: system voice + claude_prompt template + memory context + the task
    system_voice = ctx.prompts.system()
    template = ctx.prompts.load("claude_prompt")
    memory = ctx.memory.all_context()

    full_system = f"{system_voice}\n\n{template}"
    if memory:
        full_system += f"\n\n# Adam's Current Context\n\n{memory}"

    user_prompt = f"Generate a Claude.ai prompt for this task:\n\n{task}"

    # Use the note model (Qwen 14B) for prompt generation — it's better at structured output than Llama 8B
    note_model = ctx.config.get("ollama", {}).get("note_model")

    try:
        generated_prompt = ctx.ollama.generate(user_prompt, system=full_system, model=note_model)
    except Exception as e:
        return f"[error generating prompt] {e}"

    try:
        pyperclip.copy(generated_prompt)
    except Exception as e:
        return f"[generated, but clipboard failed] {e}\n\n{generated_prompt}"

    char_count = len(generated_prompt)
    return f"Prompt copied to clipboard ({char_count} chars). Paste it into Claude.ai. Go cook."