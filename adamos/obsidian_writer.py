from pathlib import Path
from datetime import datetime
from .safety import assert_within


class ObsidianWriter:
    def __init__(self, agent_inbox: str):
        self.inbox = Path(agent_inbox)
        self.inbox.mkdir(parents=True, exist_ok=True)

    def write_note(self, title: str, content: str) -> Path:
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        path = self.inbox / f"{safe_title}.md"
        assert_within(path, self.inbox)
        if path.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = self.inbox / f"{safe_title} {stamp}.md"
        path.write_text(content, encoding="utf-8")
        return path