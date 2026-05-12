HELP_TEXT = """\
AdamOS commands:

/help            Show this message
/note <topic>    Generate an Obsidian-ready note and save to Agent Inbox
/claude <task>   Generate a detailed Claude/Codex prompt, copied to clipboard
/briefing        Get a morning briefing based on your memory files
/ask <question>  Just ask the local model anything

Press Ctrl+Alt+A anywhere to summon this window.
Type anything without a slash to chat with the local model.
"""


def handle(args: str, ctx) -> str:
    return HELP_TEXT