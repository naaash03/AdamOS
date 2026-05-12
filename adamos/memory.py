from pathlib import Path


class Memory:
    def __init__(self, memory_dir: str):
        self.dir = Path(memory_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def load(self, name: str) -> str:
        path = self.dir / f"{name}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def all_context(self) -> str:
        parts = []
        for name in ["profile", "projects", "rules"]:
            content = self.load(name)
            if content.strip():
                parts.append(f"## {name}\n\n{content}")
        return "\n\n".join(parts)