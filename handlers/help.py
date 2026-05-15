HELP_TEXT = """\
AdamOS commands:

/help            Show this message
/note <topic>    Generate an Obsidian-ready note and save to Agent Inbox
/claude <task>   Generate a detailed prompt for Claude.ai, copied to clipboard
/briefing        Morning briefing based on memory and recent inbox activity

Press Ctrl+Alt+A anywhere to summon this window.
Type anything without a slash to chat with the local model.
"""


def handle(args: str, ctx) -> str:
    return HELP_TEXT