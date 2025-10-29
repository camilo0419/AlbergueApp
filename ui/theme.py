# ui/theme.py
import ttkbootstrap as tb
from tkinter import ttk

PRIMARY = "#2E86DE"
ACCENT  = "#00C4B3"
BG      = "#F7F9FC"
CARD_BG = "#FFFFFF"
BORDER  = "#E5EAF2"
TEXT    = "#1F2937"

def apply_theme(root: tb.Window):
    s = tb.Style(theme="minty")
    try:
        root.configure(bg=BG)
    except Exception:
        pass

    s.configure("TNotebook", padding=0, background=BG, borderwidth=0)
    s.configure("TNotebook.Tab", padding=(16, 10), font=("Segoe UI", 10, "bold"))
    s.map("TNotebook.Tab",
          background=[("selected", CARD_BG), ("!selected", BG)],
          foreground=[("selected", TEXT), ("!selected", "#64748B")])

    s.configure("Card.TLabelframe",
                background=CARD_BG, bordercolor=BORDER,
                relief="solid", borderwidth=1, padding=12)
    s.configure("Card.TLabelframe.Label",
                background=CARD_BG, foreground="#334155",
                font=("Segoe UI", 10, "bold"))
    s.configure("Card.TFrame", background=CARD_BG)

    s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
    s.map("Accent.TButton",
          background=[("active", ACCENT), ("!active", PRIMARY)],
          foreground=[("disabled", "#9CA3AF"), ("!disabled", "white")])

    s.configure("TEntry", padding=8)
    s.configure("TCombobox", padding=6)

    # Tablas: borde exterior y encabezado marcado
    s.configure("Modern.Treeview",
                background="white",
                fieldbackground="white",
                bordercolor=BORDER,
                lightcolor=BORDER,
                darkcolor=BORDER,
                borderwidth=1,
                rowheight=28,
                font=("Segoe UI", 9))
    s.configure("Modern.Treeview.Heading",
                font=("Segoe UI", 10, "bold"),
                relief="solid",
                bordercolor=BORDER,
                borderwidth=1,
                padding=(8, 8))
    s.map("Modern.Treeview.Heading",
          background=[("active", "#EEF2F7")])

def zebra_fill(tree: ttk.Treeview):
    tree.configure(style="Modern.Treeview")
    tree.tag_configure("odd", background="#FBFDFF")
    tree.tag_configure("even", background="#F2F6FB")

def paint_rows(tree: ttk.Treeview):
    for i, iid in enumerate(tree.get_children("")):
        tree.item(iid, tags=("even" if i % 2 == 0 else "odd",))
