from handlers import help as help_handler


class Router:
    def __init__(self, ctx):
        self.ctx = ctx
        self.routes = {
            "help": help_handler.handle,
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
        return self.ctx.ollama.generate(
            text,
            system="You are AdamOS, Adam's local assistant. Be concise and direct."
        )