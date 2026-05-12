from pathlib import Path


class SafetyError(Exception):
    pass


def assert_within(path: Path, allowed_root: Path) -> None:
    """Raise if path is not inside allowed_root. Prevents writes outside Agent Inbox."""
    path = path.resolve()
    allowed_root = allowed_root.resolve()
    if allowed_root not in path.parents and path != allowed_root:
        raise SafetyError(f"Refusing to write outside {allowed_root}: {path}")