#!/usr/bin/env python3
"""Hermes Floating Desktop Visualizer & Control Pill for Doshie.

Features:
  - Frameless, translucent floating pill on top of all windows.
  - Smooth animated state ring (Idle, Listening, Thinking, Speaking).
  - Live transcript display & quick voice engine toggle (Edge / Piper / Clone).
  - Drag-and-drop anywhere on screen.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
import tkinter as tk
import urllib.request
from tkinter import ttk


VOICE_URL = os.environ.get("YOSHI_VOICE_URL", "http://127.0.0.1:5051").rstrip("/")


class HermesVisualizerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Hermes Voice Assistant")

        # Window styling: Frameless, always on top
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="#0f172a")

        # Initial dimensions & placement at top-right
        screen_w = self.root.winfo_screenwidth()
        pill_w, pill_h = 360, 68
        x = screen_w - pill_w - 30
        y = 40
        self.root.geometry(f"{pill_w}x{pill_h}+{x}+{y}")

        # State tracking
        self.state = "idle"  # idle, listening, thinking, speaking
        self.active_engine = "edge"
        self.engines_list = ["edge", "piper", "clone"]
        self.pulse_phase = 0.0

        # Enable window dragging
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.root.bind("<ButtonPress-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)

        self._build_ui()
        self._start_animation()
        self._start_status_checker()

    def _build_ui(self):
        # Outer container frame with rounded dark glass look
        self.container = tk.Frame(self.root, bg="#0f172a", highlightbackground="#334155", highlightthickness=1)
        self.container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Left: Canvas for Animated Glowing Orb
        self.canvas = tk.Canvas(self.container, width=52, height=52, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=(10, 8), pady=6)

        # Center: Text Info (Title & Transcript/Status)
        text_frame = tk.Frame(self.container, bg="#0f172a")
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)

        self.title_label = tk.Label(
            text_frame,
            text="Hermes Assistant",
            font=("Inter", 10, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
            anchor="w",
        )
        self.title_label.pack(fill=tk.X)

        self.status_label = tk.Label(
            text_frame,
            text="Ready · Standing by",
            font=("Inter", 8),
            fg="#94a3b8",
            bg="#0f172a",
            anchor="w",
        )
        self.status_label.pack(fill=tk.X)

        # Right: Quick Controls (Engine Badge & Close)
        ctrl_frame = tk.Frame(self.container, bg="#0f172a")
        ctrl_frame.pack(side=tk.RIGHT, padx=(4, 10), pady=8)

        self.engine_btn = tk.Button(
            ctrl_frame,
            text="⚡ EDGE",
            font=("Inter", 7, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
            activebackground="#334155",
            activeforeground="#38bdf8",
            relief=tk.FLAT,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._cycle_engine,
        )
        self.engine_btn.pack(side=tk.TOP, pady=(0, 4))

        close_btn = tk.Button(
            ctrl_frame,
            text="✕",
            font=("Inter", 8),
            fg="#64748b",
            bg="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ef4444",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self.root.destroy,
        )
        close_btn.pack(side=tk.BOTTOM)

    def _start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_start_x)
        y = self.root.winfo_y() + (event.y - self.drag_start_y)
        self.root.geometry(f"+{x}+{y}")

    def _cycle_engine(self):
        idx = (self.engines_list.index(self.active_engine) + 1) % len(self.engines_list)
        self.active_engine = self.engines_list[idx]
        icons = {"edge": "⚡ EDGE", "piper": "🔊 PIPER", "clone": "🎙️ CLONE"}
        self.engine_btn.config(text=icons.get(self.active_engine, self.active_engine.upper()))
        self.status_label.config(text=f"Engine set to {self.active_engine.upper()}")

    def set_state(self, new_state: str, message: str | None = None):
        self.state = new_state
        if message:
            self.status_label.config(text=message[:38])

    def _draw_orb(self):
        self.canvas.delete("all")
        cx, cy = 26, 26

        # Colors based on state
        state_colors = {
            "idle": ("#10b981", "#059669", "#047857"),       # Emerald
            "listening": ("#38bdf8", "#0284c7", "#0369a1"),  # Sky Blue
            "thinking": ("#a855f7", "#7e22ce", "#581c87"),   # Purple
            "speaking": ("#f59e0b", "#d97706", "#b45309"),   # Amber Gold
        }
        c_glow, c_mid, c_core = state_colors.get(self.state, state_colors["idle"])

        # Pulsing radius calculation
        pulse = math.sin(self.pulse_phase) * 3.5
        r_outer = 20 + pulse
        r_mid = 14 + (pulse * 0.6)
        r_inner = 8

        # Draw outer glow aura
        self.canvas.create_oval(
            cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
            fill="", outline=c_glow, width=1.5
        )
        # Draw mid circle
        self.canvas.create_oval(
            cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid,
            fill=c_mid, outline=c_glow, width=1
        )
        # Draw inner core
        self.canvas.create_oval(
            cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner,
            fill=c_core, outline="#ffffff", width=1
        )

    def _start_animation(self):
        def animate():
            self.pulse_phase += 0.15
            self._draw_orb()
            self.root.after(40, animate)

        self.root.after(40, animate)

    def _start_status_checker(self):
        def check():
            while True:
                try:
                    req = urllib.request.Request(f"{VOICE_URL}/health")
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data.get("online") and self.state == "idle":
                            self.status_label.config(text="Ready · Standing by")
                except Exception:
                    if self.state == "idle":
                        self.status_label.config(text="Voice service offline")
                time.sleep(4.0)

        t = threading.Thread(target=check, daemon=True)
        t.start()


def main():
    root = tk.Tk()
    app = HermesVisualizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
