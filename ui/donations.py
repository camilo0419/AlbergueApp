import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.widgets import DateEntry
from db import get_conn
from ui.theme import zebra_fill, paint_rows
from ui.rounded import RoundedCard

BTN_W = 14  # ancho uniforme de botones de acciones


class DonationsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.sel_id = None

        self._build_ui()
        self.load_lookups()
        self.load_data()
        self._set_mode("new")

    # ---------------- UI ----------------
    def _build_ui(self):
        # Tarjeta superior: Formulario + Acciones
        form_card = RoundedCard(self)
        form_card.grid(row=0, column=0, sticky="ew")

        # contenedor con 2 columnas: form (flex) + acciones (fija)
        header_wrap = ttk.Frame(form_card.body, style="Card.TFrame")
        header_wrap.grid(row=0, column=0, sticky="ew")
        header_wrap.columnconfigure(0, weight=1)
        header_wrap.columnconfigure(1, weight=0, minsize=190)

        # ===== Formulario =====
        form = ttk.Frame(header_wrap, style="Card.TFrame")
        form.grid(row=0, column=0, sticky="ew")

        # fila 1
        for c in range(5):
            form.columnconfigure(c, weight=1)
        form.grid_columnconfigure(0, minsize=120)  # fecha
        form.grid_columnconfigure(1, minsize=200)  # padrino
        form.grid_columnconfigure(2, minsize=200)  # animal

        ttk.Label(form, text="Fecha").grid(row=0, column=0, sticky="w", padx=(0,4))
        ttk.Label(form, text="Padrino").grid(row=0, column=1, sticky="w", padx=(0,4))
        ttk.Label(form, text="Animal (opcional)").grid(row=0, column=2, sticky="w", padx=(0,4))
        ttk.Label(form, text="Monto").grid(row=0, column=3, sticky="w", padx=(0,4))
        ttk.Label(form, text="Método").grid(row=0, column=4, sticky="w", padx=(0,4))

        self.monto = tk.DoubleVar(value=0.0)
        self.metodo = tk.StringVar()
        self.nota   = tk.StringVar()

        self.fecha = DateEntry(form, bootstyle="info", dateformat="%Y-%m-%d", width=12)
        self.fecha.grid(row=1, column=0, sticky="ew", padx=(0,8))
        self.cmb_sponsor = ttk.Combobox(form, state="readonly")
        self.cmb_sponsor.grid(row=1, column=1, sticky="ew", padx=(0,8))
        self.cmb_animal  = ttk.Combobox(form, state="readonly")
        self.cmb_animal.grid(row=1, column=2, sticky="ew", padx=(0,8))
        ttk.Entry(form, textvariable=self.monto).grid(row=1, column=3, sticky="ew", padx=(0,8))
        ttk.Entry(form, textvariable=self.metodo).grid(row=1, column=4, sticky="ew")

        # fila 2: Nota ancha
        ttk.Label(form, text="Nota").grid(row=2, column=0, sticky="w", padx=(0,4), pady=(8,0))
        ttk.Entry(form, textvariable=self.nota)\
            .grid(row=3, column=0, columnspan=5, sticky="ew")

        # ===== Acciones (mismo tamaño) =====
        actions = ttk.Frame(header_wrap)
        actions.grid(row=0, column=1, sticky="ne")
        self.btn_save   = ttk.Button(actions, text="Guardar", style="Accent.TButton", command=self.save,   width=BTN_W)
        self.btn_update = ttk.Button(actions, text="Actualizar", command=self.update, width=BTN_W)
        self.btn_delete = ttk.Button(actions, text="Eliminar",   command=self.delete, width=BTN_W)
        self.btn_new    = ttk.Button(actions, text="Nuevo",      command=self.new,    width=BTN_W)
        for i, b in enumerate([self.btn_save, self.btn_update, self.btn_delete, self.btn_new]):
            b.grid(row=i, column=0, padx=4, pady=2, sticky="ew")

        # Tarjeta inferior: tabla
        table_card = RoundedCard(self)
        table_card.grid(row=1, column=0, sticky="nsew", pady=(8,0))

        self.tv = ttk.Treeview(
            table_card.body,
            columns=("id","fecha","padrino","animal","monto","metodo"),
            show="headings", height=16, style="Modern.Treeview"
        )
        for c,t in [("id","ID"),("fecha","Fecha"),("padrino","Padrino"),
                    ("animal","Animal"),("monto","Monto"),("metodo","Método")]:
            self.tv.heading(c, text=t)
        self.tv.column("id", width=60, anchor="center")
        self.tv.grid(row=0, column=0, sticky="nsew")
        self.tv.bind("<<TreeviewSelect>>", self.on_select)
        zebra_fill(self.tv)
        table_card.body.rowconfigure(0, weight=1)
        table_card.body.columnconfigure(0, weight=1)

        # layout root
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

    # ---------------- Modo botones ----------------
    def _set_mode(self, mode: str):
        if mode == "edit":
            self.btn_save.grid_remove()
            self.btn_update.state(["!disabled"])
            self.btn_delete.state(["!disabled"])
        else:
            if not self.btn_save.winfo_ismapped():
                self.btn_save.grid()
            self.btn_update.state(["disabled"])
            self.btn_delete.state(["disabled"])

    def new(self):
        self.tv.selection_remove(*self.tv.selection())
        self.sel_id = None
        try:
            # pone hoy sin tocar manualmente el entry
            self.fecha.set_date(None)  # limpia
        except Exception:
            pass
        # reestablece a hoy
        from datetime import date
        self.fecha.set_date(date.today())
        self.monto.set(0.0); self.metodo.set(""); self.nota.set("")
        self.cmb_sponsor.set(""); self.cmb_animal.set("")
        self._set_mode("new")

    # ---------------- Lookups / Tabla ----------------
    def _fmt(self, table, id_):
        conn = get_conn(); cur = conn.cursor()
        if table == "sponsors":
            n = cur.execute("SELECT nombre FROM sponsors WHERE id=?", (id_,)).fetchone()["nombre"]
        else:
            n = cur.execute("SELECT nombre FROM animals WHERE id=?", (id_,)).fetchone()["nombre"]
        conn.close()
        return f"{id_} - {n}"

    def load_lookups(self):
        conn = get_conn(); cur = conn.cursor()
        sponsors = cur.execute("SELECT id, nombre FROM sponsors ORDER BY nombre").fetchall()
        animals  = cur.execute("SELECT id, nombre FROM animals ORDER BY nombre").fetchall()
        self.cmb_sponsor["values"] = [f"{r['id']} - {r['nombre']}" for r in sponsors]
        self.cmb_animal["values"]  = [""] + [f"{r['id']} - {r['nombre']}" for r in animals]
        conn.close()

    def load_data(self):
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("""
            SELECT d.id, d.fecha, s.nombre AS padrino, a.nombre AS animal, d.monto, d.metodo
            FROM donations d
            JOIN sponsors s ON s.id = d.sponsor_id
            LEFT JOIN animals a ON a.id = d.animal_id
            ORDER BY d.id DESC
        """).fetchall()
        self.tv.delete(*self.tv.get_children())
        for r in rows:
            self.tv.insert("", "end", values=(r["id"], r["fecha"], r["padrino"], r["animal"], r["monto"], r["metodo"]))
        conn.close()
        paint_rows(self.tv)

    # ---------------- Selección / CRUD ----------------
    def on_select(self, _):
        sel = self.tv.selection()
        if not sel: return
        v = self.tv.item(sel[0], "values")
        self.sel_id = int(v[0])

        conn = get_conn(); cur = conn.cursor()
        r = cur.execute("SELECT * FROM donations WHERE id=?", (self.sel_id,)).fetchone()
        conn.close()
        if not r: return

        try:
            self.fecha.set_date(r["fecha"])
        except Exception:
            self.fecha.entry.delete(0, "end")
            self.fecha.entry.insert(0, r["fecha"])

        self.monto.set(r["monto"] or 0.0)
        self.metodo.set(r["metodo"] or "")
        self.nota.set(r["nota"] or "")

        self.cmb_sponsor.set(self._fmt("sponsors", r["sponsor_id"]) if r["sponsor_id"] else "")
        self.cmb_animal.set(self._fmt("animals", r["animal_id"]) if r["animal_id"] else "")

        self._set_mode("edit")

    def save(self):
        if not self.fecha.entry.get().strip() or not self.cmb_sponsor.get().strip():
            messagebox.showwarning("Falta", "Fecha y Padrino son obligatorios"); return
        sponsor_id = int(self.cmb_sponsor.get().split(" - ")[0])
        animal_id = int(self.cmb_animal.get().split(" - ")[0]) if self.cmb_animal.get().strip() else None

        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO donations(fecha, sponsor_id, animal_id, monto, metodo, nota)
            VALUES(?,?,?,?,?,?)
        """, (self.fecha.entry.get().strip(), sponsor_id, animal_id,
              float(self.monto.get() or 0.0), self.metodo.get().strip(), self.nota.get().strip()))
        conn.commit(); conn.close()
        self.new()
        self.load_data()

    def update(self):
        if not self.sel_id: return
        sponsor_id = int(self.cmb_sponsor.get().split(" - ")[0]) if self.cmb_sponsor.get().strip() else None
        animal_id = int(self.cmb_animal.get().split(" - ")[0]) if self.cmb_animal.get().strip() else None

        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            UPDATE donations
               SET fecha=?, sponsor_id=?, animal_id=?, monto=?, metodo=?, nota=?
             WHERE id=?
        """, (self.fecha.entry.get().strip(), sponsor_id, animal_id,
              float(self.monto.get() or 0.0), self.metodo.get().strip(), self.nota.get().strip(), self.sel_id))
        conn.commit(); conn.close()
        self.new()
        self.load_data()

    def delete(self):
        if not self.sel_id: return
        if not messagebox.askyesno("Eliminar", "¿Eliminar donación seleccionada?"): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM donations WHERE id=?", (self.sel_id,))
        conn.commit(); conn.close()
        self.new()
        self.load_data()

    # ---------------- API público ----------------
    def refresh(self):
        self.load_lookups()
        self.load_data()
