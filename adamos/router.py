from handlers import help as help_handler
from handlers import note as note_handler
from handlers import claude_prompt as claude_handler
from handlers import briefing as briefing_handler


class Router:
    def __init__(self, ctx):
        self.ctx = ctx
        self.routes = {
            "help": help_handler.handle,
            "note": note_handler.handle,
            "claude": claude_handler.handle,
            "briefing": briefing_handler.handle,
        }

    def dispatch(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        if text.startswith("/"):
            parts = text[1:].split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            handler = self.routes.get(cmd)
            if handler is None:
                return f"Unknown command: /{cmd}. Type /help for a list."
            return handler(args, self.ctx)
        # Free chat: use the system voice prompt plus memory
        system = self.ctx.prompts.system()
        memory = self.ctx.memory.all_context()
        full_system = f"{system}\n\n# Memory Context\n\n{memory}" if memory else system
        return self.ctx.ollama.generate(text, system=full_system)