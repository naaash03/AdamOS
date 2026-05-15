import yaml
import keyboard
from pathlib import Path
from types import SimpleNamespace

from adamos.ollama_client import OllamaClient
from adamos.obsidian_writer import ObsidianWriter
from adamos.memory import Memory
from adamos.prompt_loader import PromptLoader
from adamos.router import Router
from adamos.ui import AdamOSWindow


def load_config():
    cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        raise SystemExit("config.yaml not found. Copy config.example.yaml to config.yaml and edit the paths.")
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def main():
    cfg = load_config()

    ctx = SimpleNamespace(
        config=cfg,
        ollama=OllamaClient(cfg["ollama"]["host"], cfg["ollama"]["default_model"]),
        writer=ObsidianWriter(cfg["paths"]["agent_inbox"]),
        memory=Memory(cfg["paths"]["memory"]),
        prompts=PromptLoader(),
    )

    router = Router(ctx)
    window = AdamOSWindow(router)

    def on_hotkey():
        window.root.after(0, window.show)

    hotkey = cfg.get("hotkey", "ctrl+alt+a")
    try:
        keyboard.add_hotkey(hotkey, on_hotkey)
        print(f"AdamOS listening on {hotkey}.")
    except Exception as e:
        print(f"[warn] Could not register hotkey: {e}")
        print("You can still use the window directly.")

    window.run()


if __name__ == "__main__":
    main()