from pathlib import Path
from typing import Optional


class PromptLoader:
    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            # Anchor to project root (one level up from adamos/)
            self.dir = Path(__file__).resolve().parents[1] / "prompts"
        else:
            self.dir = Path(prompts_dir)

    def load(self, name: str) -> str:
        """Load a prompt template by name (without .md extension)."""
        path = self.dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def system(self) -> str:
        """Convenience: load the base system prompt."""
        return self.load("system")