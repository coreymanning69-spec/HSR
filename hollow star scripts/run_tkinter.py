"""Local Tkinter launcher for the Web backend."""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

ROOT = Path(__file__).resolve().parent


def main() -> int:
    root = tk.Tk()
    root.title("Hollow Star Reliquary - Local Tools")
    root.geometry("520x220")

    status = tk.StringVar(value="The Python engine runs locally; no AI service is required.")

    def launch_web() -> None:
        subprocess.Popen(
            [sys.executable, "hollowstar_web_server.py", "--port", "8765"],
            cwd=ROOT,
        )
        status.set("Local Web backend started on http://127.0.0.1:8765")

    def show_about() -> None:
        messagebox.showinfo(
            "Architecture",
            "HSRHost and RunService own rules, state, RNG, and saves.\n"
            "The Web, Pygame, and Tkinter layers are presentation adapters.",
        )

    tk.Label(root, text="Hollow Star Reliquary", font=("Segoe UI", 18, "bold")).pack(pady=18)
    tk.Label(root, textvariable=status, wraplength=460).pack(pady=4)
    buttons = tk.Frame(root)
    buttons.pack(pady=18)
    tk.Button(buttons, text="Launch Local Web", command=launch_web, width=18).pack(side=tk.LEFT, padx=6)
    tk.Button(buttons, text="About Architecture", command=show_about, width=18).pack(side=tk.LEFT, padx=6)
    tk.Button(buttons, text="Quit", command=root.destroy, width=10).pack(side=tk.LEFT, padx=6)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
