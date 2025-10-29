# ui/rounded.py
import tkinter as tk
from tkinter import ttk

class RoundedCard(ttk.Frame):
    def __init__(self, master, radius=14, bg=None, border="#E5EAF2", pad=12):
        super().__init__(master)
        self._radius = radius
        self._border = border
        self._bg = bg or self._resolve_bg()

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self._bg)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.body = ttk.Frame(self, padding=pad, style="Card.TFrame")
        self._window_id = None

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.bind("<Configure>", self._redraw)

    def _resolve_bg(self):
        try:
            style = ttk.Style()
            bg = style.lookup("TFrame", "background")
            return bg or "#F7F9FC"
        except Exception:
            return "#F7F9FC"

    def _redraw(self, *_):
        w = max(self.winfo_width(), 2 * self._radius + 2)
        h = max(self.winfo_height(), 2 * self._radius + 2)
        r = self._radius

        self.canvas.delete("all")
        self.canvas.configure(bg=self._bg)

        self.canvas.create_rectangle(r, 1, w - r, h - 1, fill="white", outline=self._border)
        self.canvas.create_rectangle(1, r, w - 1, h - r, fill="white", outline=self._border)
        self.canvas.create_oval(1, 1, 2 * r, 2 * r, fill="white", outline=self._border)
        self.canvas.create_oval(w - 2 * r - 1, 1, w - 1, 2 * r, fill="white", outline=self._border)
        self.canvas.create_oval(1, h - 2 * r - 1, 2 * r, h - 1, fill="white", outline=self._border)
        self.canvas.create_oval(w - 2 * r - 1, h - 2 * r - 1, w - 1, h - 1, fill="white", outline=self._border)

        inner_x = r // 2
        inner_y = r // 2
        inner_w = max(w - r, 10)
        inner_h = max(h - r, 10)

        self._window_id = self.canvas.create_window(
            inner_x, inner_y, window=self.body, anchor="nw", width=inner_w, height=inner_h
        )

        self.canvas.configure(scrollregion=(0, 0, w, h))
