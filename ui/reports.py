import tkinter as tk
from reportlab.graphics.barcode import code128, eanbc, usps
from tkinter import ttk, filedialog, messagebox
from datetime import date
import pandas as pd

from db import get_conn
from ui.rounded import RoundedCard
from ui.theme import zebra_fill, paint_rows

# progreso
import threading, queue

# ---------- PDF helpers ----------
def render_pdf_from_html(html: str, out_path: str) -> bool:
    try:
        from weasyprint import HTML  # type: ignore
        HTML(string=html).write_pdf(out_path)
        return True
    except Exception:
        try:
            from xhtml2pdf import pisa  # type: ignore
            with open(out_path, "wb") as f:
                pisa.CreatePDF(html, dest=f)
            return True
        except Exception as e:
            messagebox.showerror("PDF", f"No se pudo generar PDF:\n{e}")
            return False


REPORTES = [
    "Animales",
    "Tipos de animal",
    "Padrinos",
    "Adoptantes",
    "Donaciones",
    "Adopciones",
]


class BusyPopup(tk.Toplevel):
    def __init__(self, master, text="Procesando…"):
        super().__init__(master)
        self.title("Trabajando…")
        self.resizable(False, False)
        self.transient(master)

        # Fuerza que quede arriba y visible
        self.lift()
        self.attributes("-topmost", True)

        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=text).pack(anchor="w", pady=(0, 6))
        self.pb = ttk.Progressbar(frm, mode="indeterminate", length=300)
        self.pb.pack(fill="x")
        self.pb.start(12)

        # Centrado relativo a la ventana principal
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() // 2 - self.winfo_width() // 2)
            y = master.winfo_rooty() + (master.winfo_height() // 2 - self.winfo_height() // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        # Muy importante: mostrar YA
        self.deiconify()
        self.update()                 # fuerza pintado
        # quitamos grab_set (algunas combinaciones lo ocultan bajo diálogos del SO)
        # self.grab_set()

        # después de pintarse, ya no es “always on top”
        self.after(150, lambda: self.attributes("-topmost", False))

    def close(self):
        try:
            self.pb.stop()
        except Exception:
            pass
        self.destroy()


class ReportsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.current_label = tk.StringVar(value=REPORTES[0])
        self._build_ui()
        self.load_report()

    # -------------------- UI --------------------
    def _build_ui(self):
        # === BARRA SUPERIOR PLANA (mínima altura) ===
        topbar = ttk.Frame(self)                      # <- sin RoundedCard
        topbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        for c in range(3):
            topbar.columnconfigure(c, weight=0)
        topbar.columnconfigure(1, weight=1)          # combo se queda con el espacio al crecer

        ttk.Label(topbar, text="Reporte").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.cmb = ttk.Combobox(
            topbar, state="readonly", width=28,
            values=REPORTES, textvariable=self.current_label
        )
        self.cmb.grid(row=0, column=1, sticky="w")
        self.cmb.bind("<<ComboboxSelected>>", lambda _e: self.load_report())

        btns = ttk.Frame(topbar)
        btns.grid(row=0, column=2, sticky="e", padx=(12, 0))
        ttk.Button(btns, text="Descargar CSV",  command=self.export_csv,   width=14).pack(side="left", padx=3)
        ttk.Button(btns, text="Descargar Excel",command=self.export_excel, width=14).pack(side="left", padx=3)
        ttk.Button(btns, text="Descargar PDF",  command=self.export_pdf,   width=14).pack(side="left", padx=3)

        # === CARD DE DATOS (ocupa TODO el resto) ===
        data_card = RoundedCard(self)
        data_card.grid(row=1, column=0, sticky="nsew")
        data_card.body.rowconfigure(0, weight=1)
        data_card.body.columnconfigure(0, weight=1)

        wrap = ttk.Frame(data_card.body)
        wrap.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.tv = ttk.Treeview(
            wrap, columns=("c1",), show="headings",
            height=30, style="Modern.Treeview"
        )
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=vs.set)
        self.tv.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        zebra_fill(self.tv)

        # La fila 0 no tiene peso; TODO el peso a la tabla
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

    # -------------------- Helper progreso --------------------
    def _run_with_busy(self, titulo: str, worker, on_ok_msg: str):
        """Muestra BusyPopup, corre `worker` en un hilo, y al terminar cierra y notifica."""
        root = self.winfo_toplevel()
        busy = BusyPopup(root, text=titulo)
        q = queue.Queue()

        def _t():
            try:
                worker()
                q.put(("ok", None))
            except Exception as e:
                q.put(("err", e))

        # Arranca hilo y asegura que la UI se pinte antes de continuar
        threading.Thread(target=_t, daemon=True).start()
        busy.update_idletasks()
        busy.update()

        def _poll():
            try:
                kind, payload = q.get_nowait()
            except queue.Empty:
                # seguir chequeando
                self.after(60, _poll)
                return
            # cerrar popup y notificar
            try:
                busy.close()
            except Exception:
                pass

            if kind == "ok":
                messagebox.showinfo("Exportación", on_ok_msg)
            else:
                messagebox.showerror("Exportación", f"Ocurrió un error:\n{payload}")

        _poll()

    # -------------------- Data por reporte --------------------
    def _df_animales(self) -> pd.DataFrame:
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("""
            SELECT a.id AS ID, a.nombre AS Nombre, t.nombre AS Tipo,
                   a.sexo AS Sexo, a.edad_meses AS "Edad(m)", a.ingreso_fecha AS Ingreso
            FROM animals a JOIN animal_types t ON t.id=a.especie_id
            ORDER BY a.id DESC
        """).fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=["ID","Nombre","Tipo","Sexo","Edad(m)","Ingreso"])

    def _df_tipos(self) -> pd.DataFrame:
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("SELECT id AS ID, nombre AS Nombre FROM animal_types ORDER BY id DESC").fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=["ID","Nombre"])

    def _df_padrinos(self) -> pd.DataFrame:
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("""
            SELECT id AS ID, nombre AS Nombre,
                   COALESCE(telefono,'') AS Tel, COALESCE(correo,'') AS Correo
            FROM sponsors ORDER BY id DESC
        """).fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=["ID","Nombre","Tel","Correo"])

    def _df_adoptantes(self) -> pd.DataFrame:
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("""
            SELECT id AS ID, nombre AS Nombre,
                   COALESCE(documento,'') AS Doc,
                   COALESCE(telefono,'')  AS Tel,
                   COALESCE(correo,'')    AS Correo
            FROM adopters ORDER BY id DESC
        """).fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=["ID","Nombre","Doc","Tel","Correo"])

    def _df_donaciones(self) -> pd.DataFrame:
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("""
            SELECT d.id AS ID, d.fecha AS Fecha, s.nombre AS Padrino,
                   COALESCE(a.nombre,'') AS Animal, d.monto AS Monto, COALESCE(d.metodo,'') AS Método
            FROM donations d
            JOIN sponsors s ON s.id=d.sponsor_id
            LEFT JOIN animals a ON a.id=d.animal_id
            ORDER BY d.id DESC
        """).fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=["ID","Fecha","Padrino","Animal","Monto","Método"])

    def _df_adopciones(self) -> pd.DataFrame:
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("""
            SELECT ad.id AS ID, a.nombre AS Animal, ap.nombre AS Adoptante,
                   ad.estado AS Estado, COALESCE(ad.fecha_egreso,'') AS Egreso
            FROM adoptions ad
            JOIN animals a ON a.id=ad.animal_id
            JOIN adopters ap ON ap.id=ad.adopter_id
            ORDER BY ad.id DESC
        """).fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=["ID","Animal","Adoptante","Estado","Egreso"])

    def _get_df(self) -> pd.DataFrame:
        lbl = self.current_label.get()
        return {
            "Animales":        self._df_animales,
            "Tipos de animal": self._df_tipos,
            "Padrinos":        self._df_padrinos,
            "Adoptantes":      self._df_adoptantes,
            "Donaciones":      self._df_donaciones,
            "Adopciones":      self._df_adopciones,
        }[lbl]()

    # -------------------- Tabla --------------------
    def load_report(self):
        try:
            df = self._get_df()
        except Exception as e:
            messagebox.showerror("Reporte", f"No fue posible cargar el reporte:\n{e}")
            return

        self.tv.delete(*self.tv.get_children())
        if df.empty:
            self.tv["columns"] = ("_msg",)
            self.tv.heading("_msg", text="SIN REGISTROS", anchor="center")
            self.tv.column("_msg", anchor="center", width=400, stretch=True)
            return

        cols = list(df.columns)
        self.tv["columns"] = cols
        for c in cols:
            self.tv.heading(c, text=c, anchor="center")
            self.tv.column(c, anchor="center", stretch=True, width=max(90, int(1100/len(cols))))

        for _, r in df.iterrows():
            self.tv.insert("", "end", values=tuple(r.values))

        paint_rows(self.tv)

    # -------------------- Export --------------------
    def _ask_path(self, base, ext):
        return filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(ext.upper(), f"*.{ext}")],
            initialfile=f"{base}_{date.today().isoformat()}.{ext}",
            title=f"Guardar {ext.upper()}",
        )

    def export_csv(self):
        df = self._get_df()
        if df.empty: messagebox.showinfo("CSV", "No hay datos para exportar."); return
        path = self._ask_path(self.current_label.get().lower().replace(" ", "_"), "csv")
        if not path: return

        def worker():
            df.to_csv(path, index=False, encoding="utf-8-sig")

        self._run_with_busy("Generando CSV…", worker, f"Archivo guardado:\n{path}")

    def export_excel(self):
        df = self._get_df()
        if df.empty: messagebox.showinfo("Excel", "No hay datos para exportar."); return
        path = self._ask_path(self.current_label.get().lower().replace(" ", "_"), "xlsx")
        if not path: return

        def worker():
            df.to_excel(path, index=False)

        self._run_with_busy("Generando Excel…", worker, f"Archivo guardado:\n{path}")

    def export_pdf(self):
        df = self._get_df()
        if df.empty: messagebox.showinfo("PDF", "No hay datos para exportar."); return
        path = self._ask_path(self.current_label.get().lower().replace(" ", "_"), "pdf")
        if not path: return

        table = "<table border='1' cellspacing='0' cellpadding='4' style='border-collapse:collapse;width:100%;font-family:Segoe UI, sans-serif;font-size:10pt;'>"
        table += "<tr>" + "".join([f"<th style='background:#f2f6fb;text-align:center'>{c}</th>" for c in df.columns]) + "</tr>"
        for _, r in df.iterrows():
            table += "<tr>" + "".join([f"<td style='text-align:center'>{r[c] if pd.notna(r[c]) else ''}</td>" for c in df.columns]) + "</tr>"
        table += "</table>"

        html = f"""
        <html><head><meta charset="utf-8"></head>
        <body style="font-family:Segoe UI, sans-serif; color:#1F2937;">
          <h2 style="margin:0 0 8px 0">{self.current_label.get()}</h2>
          <div style="font-size:10pt; color:#64748B; margin-bottom:10px">
            Generado: {date.today().isoformat()}
          </div>
          {table}
          <div style="font-size:9pt; color:#64748B; margin-top:8px">AlbergueApp</div>
        </body></html>
        """

        def worker():
            ok = render_pdf_from_html(html, path)
            if not ok:
                raise RuntimeError("No fue posible generar el PDF.")

        self._run_with_busy("Generando PDF…", worker, f"Archivo guardado:\n{path}")
