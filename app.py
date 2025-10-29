# app.py
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from datetime import date

from db import init_db
from ui.theme import apply_theme

# Pestañas / módulos principales
from ui.dashboard import DashboardFrame
from ui.animals import AnimalsFrame
from ui.sponsors import SponsorsFrame
from ui.donations import DonationsFrame
from ui.health import HealthFrame
from ui.adoptions import AdoptionsFrame
from ui.reports import ReportsFrame

APP_TITLE = "AlbergueApp"


# ----------------- Utilidades de ventana -----------------
def project_root() -> Path:
    """Carpeta raíz del proyecto (donde viven /ui, /assets, etc.)."""
    return Path(__file__).resolve().parent


def assets_path(*parts) -> str:
    """Ruta a /assets/<...>."""
    return str(project_root().joinpath("assets", *parts))


def set_app_icons(win: tk.Tk):
    """
    Intenta definir el ícono de la aplicación:
    - En Windows: .ico con iconbitmap (barra de título / taskbar).
    - En todas:   .png con wm_iconphoto como alternativa/soporte.
    Mantiene una referencia a PhotoImage para que no sea recolectada.
    """
    # Primero intentamos con .ico (Windows)
    ico = assets_path("logo.ico")
    if os.path.exists(ico):
        try:
            win.iconbitmap(ico)
        except Exception:
            # Algunas plataformas no aceptan .ico; seguimos con png
            pass

    # Luego intentamos con .png (todas las plataformas)
    png = assets_path("logo.png")
    if os.path.exists(png):
        try:
            # Guardar referencia para que Tk no lo libere
            win._app_logo_png = tk.PhotoImage(file=png)
            win.wm_iconphoto(True, win._app_logo_png)
        except Exception:
            pass


def enable_windows_hidpi():
    """
    Mejora nitidez en Windows (opcional).
    No revienta en otras plataformas.
    """
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # SYSTEM_AWARE
    except Exception:
        pass


def toggle_fullscreen(win: tk.Tk, on: bool | None = None):
    """Alterna el modo fullscreen (F11)."""
    if on is None:
        on = not bool(win.attributes("-fullscreen"))
    win.attributes("-fullscreen", on)


def on_tab_changed(event):
    """Si el tab activo tiene .refresh(), lo llama automáticamente."""
    nb: ttk.Notebook = event.widget
    sel = nb.select()
    if not sel:
        return
    frame = nb.nametowidget(sel)
    if hasattr(frame, "refresh"):
        try:
            frame.refresh()
        except Exception:
            # Evita que un fallo en refresh rompa toda la UI
            pass


def center_on_screen(win: tk.Tk, width: int, height: int):
    """Centra la ventana en pantalla con el tamaño dado."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max((sw - width) // 2, 0)
    y = max((sh - height) // 2, 0)
    win.geometry(f"{width}x{height}+{x}+{y}")


# ----------------- Main -----------------
def main():
    # Mejora de nitidez en Windows
    enable_windows_hidpi()

    # Inicializa base de datos
    init_db()

    # Ventana principal
    app = tb.Window(themename="flatly")
    apply_theme(app)
    app.title(APP_TITLE)

    # Íconos (usa assets/logo.ico y assets/logo.png si existen)
    set_app_icons(app)

    # Abrir grande pero NO en pantalla completa
    app.attributes("-fullscreen", False)   # aseguramos que no quede en fullscreen
    app.minsize(1100, 700)                 # tamaño mínimo cómodo
    center_on_screen(app, 1280, 800)       # tamaño inicial y centrada

    # Atajos: F11 alterna / Esc sale del modo pantalla completa
    app.bind("<F11>", lambda e: toggle_fullscreen(app))
    app.bind("<Escape>", lambda e: toggle_fullscreen(app, False))

    # Contenedor de pestañas
    nb = ttk.Notebook(app)
    nb.pack(fill="both", expand=True)

    # Instancia de cada módulo
    home      = DashboardFrame(nb)
    animals   = AnimalsFrame(nb)
    sponsors  = SponsorsFrame(nb)
    donations = DonationsFrame(nb)
    health    = HealthFrame(nb)
    adoptions = AdoptionsFrame(nb)
    reports   = ReportsFrame(nb)

    # --- Notificación de salud (una sola vez al inicio, con nombres) ---
    try:
        upcoming = home._pending(30)
        today = date.today()
        soon = [r for r in upcoming if (r[2] - today).days <= 7]
        if soon:
            # Solo nombres válidos (sin números ni vacíos)
            nombres = sorted({r[1] for r in soon if r[1] and not str(r[1]).isdigit()})
            lista = "\n - " + "\n - ".join(nombres[:15])  # máximo 15 nombres visibles
            if len(nombres) > 15:
                lista += "\n..."
            messagebox.showinfo(
                "Recordatorio de salud",
                f"Tienes {len(soon)} aplicaciones (vacunas/desparas) próximas en ≤7 días.\n\nAnimales:{lista}"
            )
    except Exception as e:
        print("Aviso de salud no disponible:", e)


    # Pestañas del sistema
    nb.add(home, text="Inicio")
    nb.add(animals, text="Animales")
    nb.add(sponsors, text="Padrinos")
    nb.add(donations, text="Donaciones")
    nb.add(health, text="Vacunas/Despar.")
    nb.add(adoptions, text="Adopciones")
    nb.add(reports, text="Reportes")

    # Auto-refresh al cambiar de pestaña
    nb.bind("<<NotebookTabChanged>>", on_tab_changed)

    # Ejecutar aplicación
    app.mainloop()


if __name__ == "__main__":
    main()
