import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta, datetime
from ttkbootstrap.widgets import DateEntry

from db import get_conn
from ui.rounded import RoundedCard
from ui.theme import zebra_fill, paint_rows

BTN_W = 12  # botones un poco más compactos


class HealthFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)

        self.sel_vac_id = None
        self.sel_dew_id = None
        self.animals_cache = []

        self._build_ui()
        self.load_lookups()
        self.load_pending()
        self.load_vaccines()
        self.load_deworms()
        self._set_v_mode("new")
        self._set_d_mode("new")

    # ===================== UI =====================
    def _build_ui(self):
        # ---------- Pendientes ----------
        top = RoundedCard(self)
        top.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        head = ttk.Frame(top.body)
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="Pendientes de Salud (30 días)", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(head, text="Refrescar", style="Accent.TButton", command=self.load_pending).grid(
            row=0, column=1, padx=8
        )

        self.pending_tv = ttk.Treeview(
            top.body, columns=("tipo", "animal", "proxima", "dias"), show="headings", height=6, style="Modern.Treeview"
        )
        for c, t in [("tipo", "Tipo"), ("animal", "Animal"), ("proxima", "Próxima"), ("dias", "Días")]:
            self.pending_tv.heading(c, text=t)
        self.pending_tv.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        zebra_fill(self.pending_tv)
        top.body.rowconfigure(1, weight=1)
        top.body.columnconfigure(0, weight=1)

        # ========= Izquierda: VACUNAS =========
        vac_card = RoundedCard(self)
        vac_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(vac_card.body, text="Vacunas", font=("", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))

        v_wrap = ttk.Frame(vac_card.body, style="Card.TFrame")
        v_wrap.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        v_wrap.columnconfigure(0, weight=1)  # form
        v_wrap.columnconfigure(1, weight=0, minsize=180)  # acciones

        # --- form vacunas ---
        v_form = ttk.Frame(v_wrap, style="Card.TFrame")
        v_form.grid(row=0, column=0, sticky="ew")
        for c in range(4):
            v_form.columnconfigure(c, weight=1)
        v_form.grid_columnconfigure(0, minsize=220)

        ttk.Label(v_form, text="Animal").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Label(v_form, text="Vacuna").grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Label(v_form, text="Aplicación").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Label(v_form, text="Próxima").grid(row=0, column=3, sticky="w", padx=(0, 4))

        self.v_animal = ttk.Combobox(v_form, state="readonly")
        self.v_animal.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.v_vacuna = tk.StringVar()
        ttk.Entry(v_form, textvariable=self.v_vacuna).grid(row=1, column=1, sticky="ew", padx=(0, 8))
        # width=12 + padding para que se vea bien el botón del calendario
        self.v_aplic = DateEntry(v_form, bootstyle="info", dateformat="%Y-%m-%d", width=12)
        self.v_aplic.grid(row=1, column=2, sticky="w", padx=(0, 8))
        self.v_next = DateEntry(v_form, bootstyle="info", dateformat="%Y-%m-%d", width=12)
        self.v_next.grid(row=1, column=3, sticky="w")

        ttk.Label(v_form, text="Notas").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=(8, 0))
        self.v_notas = tk.StringVar()
        ttk.Entry(v_form, textvariable=self.v_notas).grid(row=3, column=0, columnspan=4, sticky="ew")

        # acciones vacunas
        v_act = ttk.Frame(v_wrap)
        v_act.grid(row=0, column=1, sticky="ne")
        self.btn_v_save = ttk.Button(v_act, text="Guardar", style="Accent.TButton", command=self.v_save, width=BTN_W)
        self.btn_v_update = ttk.Button(v_act, text="Actualizar", command=self.v_update, width=BTN_W)
        self.btn_v_delete = ttk.Button(v_act, text="Eliminar", command=self.v_delete, width=BTN_W)
        self.btn_v_new = ttk.Button(v_act, text="Nuevo", command=self.v_new, width=BTN_W)
        for i, b in enumerate([self.btn_v_save, self.btn_v_update, self.btn_v_delete, self.btn_v_new]):
            b.grid(row=i, column=0, padx=4, pady=2, sticky="ew")

        ttk.Separator(vac_card.body, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(2, 6))

        # tabla vacunas
        self.v_tv = ttk.Treeview(
            vac_card.body, columns=("id", "animal", "vacuna", "aplic", "next"), show="headings", height=8, style="Modern.Treeview"
        )
        for c, t in [("id", "ID"), ("animal", "Animal"), ("vacuna", "Vacuna"), ("aplic", "Aplicación"), ("next", "Próxima")]:
            self.v_tv.heading(c, text=t)
        self.v_tv.column("id", width=60, anchor="center")
        self.v_tv.grid(row=3, column=0, sticky="nsew")
        self.v_tv.bind("<<TreeviewSelect>>", self.on_select_vaccine)
        zebra_fill(self.v_tv)
        vac_card.body.rowconfigure(3, weight=1)
        vac_card.body.columnconfigure(0, weight=1)

        # ========= Derecha: DESPARASITACIONES =========
        dew_card = RoundedCard(self)
        dew_card.grid(row=1, column=1, sticky="nsew")
        ttk.Label(dew_card.body, text="Desparasitaciones", font=("", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        d_wrap = ttk.Frame(dew_card.body, style="Card.TFrame")
        d_wrap.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        d_wrap.columnconfigure(0, weight=1)
        d_wrap.columnconfigure(1, weight=0, minsize=180)

        d_form = ttk.Frame(d_wrap, style="Card.TFrame")
        d_form.grid(row=0, column=0, sticky="ew")
        for c in range(4):
            d_form.columnconfigure(c, weight=1)
        d_form.grid_columnconfigure(0, minsize=220)

        ttk.Label(d_form, text="Animal").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Label(d_form, text="Producto").grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Label(d_form, text="Aplicación").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Label(d_form, text="Próxima").grid(row=0, column=3, sticky="w", padx=(0, 4))

        self.d_animal = ttk.Combobox(d_form, state="readonly")
        self.d_animal.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.d_prod = tk.StringVar()
        ttk.Entry(d_form, textvariable=self.d_prod).grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.d_aplic = DateEntry(d_form, bootstyle="info", dateformat="%Y-%m-%d", width=12)
        self.d_aplic.grid(row=1, column=2, sticky="w", padx=(0, 8))
        self.d_next = DateEntry(d_form, bootstyle="info", dateformat="%Y-%m-%d", width=12)
        self.d_next.grid(row=1, column=3, sticky="w")

        ttk.Label(d_form, text="Notas").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=(8, 0))
        self.d_notas = tk.StringVar()
        ttk.Entry(d_form, textvariable=self.d_notas).grid(row=3, column=0, columnspan=4, sticky="ew")

        # acciones desparasitaciones
        d_act = ttk.Frame(d_wrap)
        d_act.grid(row=0, column=1, sticky="ne")
        self.btn_d_save = ttk.Button(d_act, text="Guardar", style="Accent.TButton", command=self.d_save, width=BTN_W)
        self.btn_d_update = ttk.Button(d_act, text="Actualizar", command=self.d_update, width=BTN_W)
        self.btn_d_delete = ttk.Button(d_act, text="Eliminar", command=self.d_delete, width=BTN_W)
        self.btn_d_new = ttk.Button(d_act, text="Nuevo", command=self.d_new, width=BTN_W)
        for i, b in enumerate([self.btn_d_save, self.btn_d_update, self.btn_d_delete, self.btn_d_new]):
            b.grid(row=i, column=0, padx=4, pady=2, sticky="ew")

        ttk.Separator(dew_card.body, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(2, 6))

        self.d_tv = ttk.Treeview(
            dew_card.body, columns=("id", "animal", "producto", "aplic", "next"), show="headings", height=8, style="Modern.Treeview"
        )
        for c, t in [("id", "ID"), ("animal", "Animal"), ("producto", "Producto"), ("aplic", "Aplicación"), ("next", "Próxima")]:
            self.d_tv.heading(c, text=t)
        self.d_tv.column("id", width=60, anchor="center")
        self.d_tv.grid(row=3, column=0, sticky="nsew")
        self.d_tv.bind("<<TreeviewSelect>>", self.on_select_deworm)
        zebra_fill(self.d_tv)
        dew_card.body.rowconfigure(3, weight=1)
        dew_card.body.columnconfigure(0, weight=1)

        # layout root
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    # ===================== modos =====================
    def _set_v_mode(self, mode):
        if mode == "edit":
            self.btn_v_save.grid_remove()
            self.btn_v_update.state(["!disabled"])
            self.btn_v_delete.state(["!disabled"])
        else:
            if not self.btn_v_save.winfo_ismapped():
                self.btn_v_save.grid()
            self.btn_v_update.state(["disabled"])
            self.btn_v_delete.state(["disabled"])

    def _set_d_mode(self, mode):
        if mode == "edit":
            self.btn_d_save.grid_remove()
            self.btn_d_update.state(["!disabled"])
            self.btn_d_delete.state(["!disabled"])
        else:
            if not self.btn_d_save.winfo_ismapped():
                self.btn_d_save.grid()
            self.btn_d_update.state(["disabled"])
            self.btn_d_delete.state(["disabled"])

    # ===================== datos base =====================
    def load_lookups(self):
        conn = get_conn()
        cur = conn.cursor()
        self.animals_cache = cur.execute("SELECT id, nombre FROM animals ORDER BY nombre").fetchall()
        values = [f"{r['id']} - {r['nombre']}" for r in self.animals_cache]
        for cmb in (self.v_animal, self.d_animal):
            cmb["values"] = values
        conn.close()

    # ===================== pendientes =====================
    def load_pending(self, days=30):
        """Solo próximos entre hoy y hoy+days; NO muestra vencidos ni días negativos."""
        self.pending_tv.delete(*self.pending_tv.get_children())
        today = date.today()
        limit = today + timedelta(days=days)
        rows = []

        conn = get_conn()
        cur = conn.cursor()
        for table, label in [("vaccines", "Vacuna"), ("dewormings", "Desparasitación")]:
            q = f"""
                SELECT '{label}' as tipo, a.nombre as animal, t.proxima_fecha
                FROM {table} t JOIN animals a ON a.id=t.animal_id
                WHERE t.proxima_fecha IS NOT NULL AND t.proxima_fecha <> ''
            """
            for r in cur.execute(q):
                try:
                    d = datetime.strptime(r["proxima_fecha"], "%Y-%m-%d").date()
                    if today <= d <= limit:
                        rows.append((label, r["animal"], d))
                except Exception:
                    pass
        conn.close()

        rows.sort(key=lambda x: x[2])
        for t, animal, d in rows:
            delta = (d - today).days
            tag = "soon" if delta <= 7 else "ok"
            self.pending_tv.insert("", "end", values=(t, animal, d.isoformat(), delta), tags=(tag,))
        # Colores (solo dos estados)
        self.pending_tv.tag_configure("soon", background="#FEF3C7")
        self.pending_tv.tag_configure("ok", background="#F2F6FB")
        paint_rows(self.pending_tv)

    # ===================== vacunas =====================
    def load_vaccines(self):
        conn = get_conn()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT v.id, a.nombre AS animal, v.vacuna, v.fecha_aplicacion, v.proxima_fecha
            FROM vaccines v JOIN animals a ON a.id=v.animal_id
            ORDER BY v.id DESC
        """
        ).fetchall()
        self.v_tv.delete(*self.v_tv.get_children())
        for r in rows:
            self.v_tv.insert(
                "", "end", values=(r["id"], r["animal"], r["vacuna"], r["fecha_aplicacion"], r["proxima_fecha"])
            )
        conn.close()
        paint_rows(self.v_tv)

    def on_select_vaccine(self, _):
        sel = self.v_tv.selection()
        if not sel:
            return
        v = self.v_tv.item(sel[0], "values")
        self.sel_vac_id = int(v[0])

        conn = get_conn()
        cur = conn.cursor()
        r = cur.execute("SELECT * FROM vaccines WHERE id=?", (self.sel_vac_id,)).fetchone()
        conn.close()
        if not r:
            return

        self.v_animal.set(self._fmt_animal(r["animal_id"]))
        self.v_vacuna.set(r["vacuna"] or "")
        try:
            self.v_aplic.set_date(r["fecha_aplicacion"])
        except Exception:
            self.v_aplic.entry.delete(0, "end")
            self.v_aplic.entry.insert(0, r["fecha_aplicacion"] or "")
        try:
            self.v_next.set_date(r["proxima_fecha"] or "")
        except Exception:
            self.v_next.entry.delete(0, "end")
            self.v_next.entry.insert(0, r["proxima_fecha"] or "")
        self.v_notas.set(r["notas"] or "")
        self._set_v_mode("edit")

    def v_new(self):
        self.v_tv.selection_remove(*self.v_tv.selection())
        self.sel_vac_id = None
        self.v_animal.set("")
        self.v_vacuna.set("")
        self.v_notas.set("")
        self.v_aplic.set_date(date.today())
        self.v_next.set_date(date.today())
        self._set_v_mode("new")

    def v_save(self):
        if not self.v_animal.get().strip() or not self.v_vacuna.get().strip():
            messagebox.showwarning("Falta", "Animal y Vacuna son obligatorios")
            return
        animal_id = int(self.v_animal.get().split(" - ")[0])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO vaccines(animal_id, vacuna, fecha_aplicacion, proxima_fecha, notas)
            VALUES(?,?,?,?,?)
        """,
            (
                animal_id,
                self.v_vacuna.get().strip(),
                self.v_aplic.entry.get().strip(),
                self.v_next.entry.get().strip(),
                self.v_notas.get().strip(),
            ),
        )
        conn.commit()
        conn.close()
        self.v_new()
        self.load_vaccines()
        self.load_pending()

    def v_update(self):
        if not self.sel_vac_id:
            return
        animal_id = int(self.v_animal.get().split(" - ")[0]) if self.v_animal.get().strip() else None
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE vaccines
               SET animal_id=?, vacuna=?, fecha_aplicacion=?, proxima_fecha=?, notas=?
             WHERE id=?
        """,
            (
                animal_id,
                self.v_vacuna.get().strip(),
                self.v_aplic.entry.get().strip(),
                self.v_next.entry.get().strip(),
                self.v_notas.get().strip(),
                self.sel_vac_id,
            ),
        )
        conn.commit()
        conn.close()
        self.v_new()
        self.load_vaccines()
        self.load_pending()

    def v_delete(self):
        if not self.sel_vac_id:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar registro de vacuna?"):
            return
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM vaccines WHERE id=?", (self.sel_vac_id,))
        conn.commit()
        conn.close()
        self.v_new()
        self.load_vaccines()
        self.load_pending()

    # ===================== desparasitaciones =====================
    def load_deworms(self):
        conn = get_conn()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT d.id, a.nombre AS animal, d.producto, d.fecha_aplicacion, d.proxima_fecha
            FROM dewormings d JOIN animals a ON a.id=d.animal_id
            ORDER BY d.id DESC
        """
        ).fetchall()
        self.d_tv.delete(*self.d_tv.get_children())
        for r in rows:
            self.d_tv.insert(
                "", "end", values=(r["id"], r["animal"], r["producto"], r["fecha_aplicacion"], r["proxima_fecha"])
            )
        conn.close()
        paint_rows(self.d_tv)

    def on_select_deworm(self, _):
        sel = self.d_tv.selection()
        if not sel:
            return
        v = self.d_tv.item(sel[0], "values")
        self.sel_dew_id = int(v[0])
        conn = get_conn()
        cur = conn.cursor()
        r = cur.execute("SELECT * FROM dewormings WHERE id=?", (self.sel_dew_id,)).fetchone()
        conn.close()
        if not r:
            return

        self.d_animal.set(self._fmt_animal(r["animal_id"]))
        self.d_prod.set(r["producto"] or "")
        try:
            self.d_aplic.set_date(r["fecha_aplicacion"])
        except Exception:
            self.d_aplic.entry.delete(0, "end")
            self.d_aplic.entry.insert(0, r["fecha_aplicacion"] or "")
        try:
            self.d_next.set_date(r["proxima_fecha"] or "")
        except Exception:
            self.d_next.entry.delete(0, "end")
            self.d_next.entry.insert(0, r["proxima_fecha"] or "")
        self.d_notas.set(r["notas"] or "")
        self._set_d_mode("edit")

    def d_new(self):
        self.d_tv.selection_remove(*self.d_tv.selection())
        self.sel_dew_id = None
        self.d_animal.set("")
        self.d_prod.set("")
        self.d_notas.set("")
        self.d_aplic.set_date(date.today())
        self.d_next.set_date(date.today())
        self._set_d_mode("new")

    def d_save(self):
        if not self.d_animal.get().strip() or not self.d_prod.get().strip():
            messagebox.showwarning("Falta", "Animal y Producto son obligatorios")
            return
        animal_id = int(self.d_animal.get().split(" - ")[0])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dewormings(animal_id, producto, fecha_aplicacion, proxima_fecha, notas)
            VALUES(?,?,?,?,?)
        """,
            (
                animal_id,
                self.d_prod.get().strip(),
                self.d_aplic.entry.get().strip(),
                self.d_next.entry.get().strip(),
                self.d_notas.get().strip(),
            ),
        )
        conn.commit()
        conn.close()
        self.d_new()
        self.load_deworms()
        self.load_pending()

    def d_update(self):
        if not self.sel_dew_id:
            return
        animal_id = int(self.d_animal.get().split(" - ")[0]) if self.d_animal.get().strip() else None
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dewormings
               SET animal_id=?, producto=?, fecha_aplicacion=?, proxima_fecha=?, notas=?
             WHERE id=?
        """,
            (
                animal_id,
                self.d_prod.get().strip(),
                self.d_aplic.entry.get().strip(),
                self.d_next.entry.get().strip(),
                self.d_notas.get().strip(),
                self.sel_dew_id,
            ),
        )
        conn.commit()
        conn.close()
        self.d_new()
        self.load_deworms()
        self.load_pending()

    def d_delete(self):
        if not self.sel_dew_id:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar registro de desparasitación?"):
            return
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM dewormings WHERE id=?", (self.sel_dew_id,))
        conn.commit()
        conn.close()
        self.d_new()
        self.load_deworms()
        self.load_pending()

    # ===================== helpers =====================
    def _fmt_animal(self, animal_id: int | None) -> str:
        if not animal_id:
            return ""
        for r in self.animals_cache:
            if r["id"] == animal_id:
                return f"{r['id']} - {r['nombre']}"
        conn = get_conn()
        cur = conn.cursor()
        n = cur.execute("SELECT nombre FROM animals WHERE id=?", (animal_id,)).fetchone()
        conn.close()
        return f"{animal_id} - {n['nombre'] if n else ''}"

    # API público
    def refresh(self):
        self.load_lookups()
        self.load_pending()
        self.load_vaccines()
        self.load_deworms()
