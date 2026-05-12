import customtkinter as ctk
import threading


class AdamOSWindow:
    def __init__(self, router):
        self.router = router
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("AdamOS")
        self.root.geometry("700x500")
        self.root.attributes("-topmost", True)

        self.output = ctk.CTkTextbox(self.root, wrap="word", font=("Consolas", 12))
        self.output.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        self.output.insert("end", "AdamOS ready. Type /help to begin.\n\n")
        self.output.configure(state="disabled")

        self.entry = ctk.CTkEntry(self.root, font=("Consolas", 13), height=40)
        self.entry.pack(fill="x", padx=10, pady=(0, 10))
        self.entry.bind("<Return>", self.on_submit)
        self.entry.focus()

    def on_submit(self, _event):
        text = self.entry.get()
        if not text.strip():
            return
        self.entry.delete(0, "end")
        self.append(f"> {text}\n")
        self.append("...\n")
        threading.Thread(target=self._run_dispatch, args=(text,), daemon=True).start()

    def _run_dispatch(self, text: str):
        try:
            response = self.router.dispatch(text)
        except Exception as e:
            response = f"[error] {e}"
        self.root.after(0, self._replace_thinking, response)

    def _replace_thinking(self, response: str):
        self.output.configure(state="normal")
        self.output.delete("end-2l", "end-1l")
        self.output.insert("end", f"{response}\n\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def append(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus()

    def run(self):
        self.root.mainloop()