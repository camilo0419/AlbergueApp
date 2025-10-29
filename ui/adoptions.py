import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.widgets import DateEntry

from db import get_conn
from ui.theme import zebra_fill, paint_rows
from ui.rounded import RoundedCard

ESTADOS = ["EN_PROCESO", "ADOPTADO", "RECHAZADO"]
BTN_W = 14  # ancho uniforme para acciones


class AdoptionsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)

        self.sel_adopter_id = None
        self.sel_adoption_id = None

        self._build_ui()
        self.load_lookups()
        self.load_tables()
        self._set_mode_adopter("new")
        self._set_mode_adoption("new")

    # ===================== UI =====================
    def _build_ui(self):
        # --------- Tarjeta: ADOPTANTES ---------
        adop_card = RoundedCard(self)
        adop_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(adop_card.body, text="Adoptantes", font=("", 12, "bold")) \
            .grid(row=0, column=0, sticky="w", pady=(0, 6))

        a_wrap = ttk.Frame(adop_card.body, style="Card.TFrame")
        a_wrap.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        a_wrap.columnconfigure(0, weight=1)
        a_wrap.columnconfigure(1, weight=0, minsize=170)  # un poco más compacto

        a_form = ttk.Frame(a_wrap, style="Card.TFrame")
        a_form.grid(row=0, column=0, sticky="ew")
        for c in range(4):
            a_form.columnconfigure(c, weight=1)

        self.ad_nombre = tk.StringVar()
        self.ad_doc = tk.StringVar()
        self.ad_tel = tk.StringVar()
        self.ad_correo = tk.StringVar()
        self.ad_dir = tk.StringVar()

        ttk.Label(a_form, text="Nombre").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Entry(a_form, textvariable=self.ad_nombre).grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(a_form, text="Documento").grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Entry(a_form, textvariable=self.ad_doc).grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(a_form, text="Tel").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Entry(a_form, textvariable=self.ad_tel).grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(a_form, text="Correo").grid(row=0, column=3, sticky="w", padx=(0, 4))
        ttk.Entry(a_form, textvariable=self.ad_correo).grid(row=1, column=3, sticky="ew")

        ttk.Label(a_form, text="Dirección").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=(8, 0))
        ttk.Entry(a_form, textvariable=self.ad_dir).grid(row=3, column=0, columnspan=4, sticky="ew")

        a_act = ttk.Frame(a_wrap)
        a_act.grid(row=0, column=1, sticky="ne")
        self.btn_a_save = ttk.Button(a_act, text="Guardar", style="Accent.TButton",
                                     command=self.save_adopter, width=BTN_W)
        self.btn_a_update = ttk.Button(a_act, text="Actualizar", command=self.update_adopter, width=BTN_W)
        self.btn_a_delete = ttk.Button(a_act, text="Eliminar", command=self.delete_adopter, width=BTN_W)
        self.btn_a_new = ttk.Button(a_act, text="Nuevo", command=self.new_adopter, width=BTN_W)
        for i, b in enumerate([self.btn_a_save, self.btn_a_update, self.btn_a_delete, self.btn_a_new]):
            b.grid(row=i, column=0, padx=4, pady=2, sticky="ew")

        # tabla adoptantes + scrollbar
        tbl_wrap_a = ttk.Frame(adop_card.body)
        tbl_wrap_a.grid(row=2, column=0, sticky="nsew")
        self.tv_adopters = ttk.Treeview(
            tbl_wrap_a,
            columns=("id", "nombre", "doc", "tel", "correo"),
            show="headings", height=14, style="Modern.Treeview"
        )
        for c, t in [("id", "ID"), ("nombre", "Nombre"), ("doc", "Doc"),
                     ("tel", "Tel"), ("correo", "Correo")]:
            self.tv_adopters.heading(c, text=t)
        self.tv_adopters.column("id", width=60, anchor="center")
        vs_a = ttk.Scrollbar(tbl_wrap_a, orient="vertical", command=self.tv_adopters.yview)
        self.tv_adopters.configure(yscrollcommand=vs_a.set)
        self.tv_adopters.grid(row=0, column=0, sticky="nsew")
        vs_a.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        tbl_wrap_a.rowconfigure(0, weight=1); tbl_wrap_a.columnconfigure(0, weight=1)

        self.tv_adopters.bind("<<TreeviewSelect>>", self.on_select_adopter)
        zebra_fill(self.tv_adopters)
        adop_card.body.rowconfigure(2, weight=1)
        adop_card.body.columnconfigure(0, weight=1)

        # --------- Tarjeta: ADOPCIONES ---------
        adp_card = RoundedCard(self)
        adp_card.grid(row=0, column=1, sticky="nsew")

        ttk.Label(adp_card.body, text="Adopciones", font=("", 12, "bold")) \
            .grid(row=0, column=0, sticky="w", pady=(0, 6))

        d_wrap = ttk.Frame(adp_card.body, style="Card.TFrame")
        d_wrap.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        d_wrap.columnconfigure(0, weight=1)
        d_wrap.columnconfigure(1, weight=0, minsize=170)

        d_form = ttk.Frame(d_wrap, style="Card.TFrame")
        d_form.grid(row=0, column=0, sticky="ew")
        for c in range(4):
            d_form.columnconfigure(c, weight=1)

        self.cmb_animal = ttk.Combobox(d_form, state="readonly")
        self.cmb_adopter = ttk.Combobox(d_form, state="readonly")
        self.estado = tk.StringVar(value=ESTADOS[0])
        self.egreso = DateEntry(d_form, bootstyle="info", dateformat="%Y-%m-%d", width=12)
        self.obs = tk.StringVar()

        ttk.Label(d_form, text="Animal").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.cmb_animal.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(d_form, text="Adoptante").grid(row=0, column=1, sticky="w", padx=(0, 4))
        self.cmb_adopter.grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(d_form, text="Estado").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Combobox(d_form, textvariable=self.estado, values=ESTADOS, state="readonly") \
            .grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(d_form, text="Egreso").grid(row=0, column=3, sticky="w", padx=(0, 4))
        self.egreso.grid(row=1, column=3, sticky="w")

        ttk.Label(d_form, text="Obs").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=(8, 0))
        ttk.Entry(d_form, textvariable=self.obs).grid(row=3, column=0, columnspan=4, sticky="ew")

        d_act = ttk.Frame(d_wrap)
        d_act.grid(row=0, column=1, sticky="ne")
        self.btn_d_save = ttk.Button(d_act, text="Guardar", style="Accent.TButton",
                                     command=self.save_adoption, width=BTN_W)
        self.btn_d_update = ttk.Button(d_act, text="Actualizar", command=self.update_adoption, width=BTN_W)
        self.btn_d_delete = ttk.Button(d_act, text="Eliminar", command=self.delete_adoption, width=BTN_W)
        self.btn_d_new = ttk.Button(d_act, text="Nuevo", command=self.new_adoption, width=BTN_W)
        for i, b in enumerate([self.btn_d_save, self.btn_d_update, self.btn_d_delete, self.btn_d_new]):
            b.grid(row=i, column=0, padx=4, pady=2, sticky="ew")

        # tabla adopciones + scrollbar
        tbl_wrap_d = ttk.Frame(adp_card.body)
        tbl_wrap_d.grid(row=2, column=0, sticky="nsew")
        self.tv_adoptions = ttk.Treeview(
            tbl_wrap_d,
            columns=("id", "animal", "adoptante", "estado", "egreso"),
            show="headings", height=14, style="Modern.Treeview"
        )
        for c, t in [("id", "ID"), ("animal", "Animal"), ("adoptante", "Adoptante"),
                     ("estado", "Estado"), ("egreso", "Egreso")]:
            self.tv_adoptions.heading(c, text=t)
        self.tv_adoptions.column("id", width=60, anchor="center")
        vs_d = ttk.Scrollbar(tbl_wrap_d, orient="vertical", command=self.tv_adoptions.yview)
        self.tv_adoptions.configure(yscrollcommand=vs_d.set)
        self.tv_adoptions.grid(row=0, column=0, sticky="nsew")
        vs_d.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        tbl_wrap_d.rowconfigure(0, weight=1); tbl_wrap_d.columnconfigure(0, weight=1)

        self.tv_adoptions.bind("<<TreeviewSelect>>", self.on_select_adoption)
        zebra_fill(self.tv_adoptions)
        adp_card.body.rowconfigure(2, weight=1)
        adp_card.body.columnconfigure(0, weight=1)

        # layout raíz: ¡esto permite “bajar” y que crezcan!
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

    # ===================== Modos botones =====================
    def _set_mode_adopter(self, mode: str):
        if mode == "edit":
            self.btn_a_save.grid_remove()
            self.btn_a_update.state(["!disabled"])
            self.btn_a_delete.state(["!disabled"])
        else:
            if not self.btn_a_save.winfo_ismapped():
                self.btn_a_save.grid()
            self.btn_a_update.state(["disabled"])
            self.btn_a_delete.state(["disabled"])

    def _set_mode_adoption(self, mode: str):
        if mode == "edit":
            self.btn_d_save.grid_remove()
            self.btn_d_update.state(["!disabled"])
            self.btn_d_delete.state(["!disabled"])
        else:
            if not self.btn_d_save.winfo_ismapped():
                self.btn_d_save.grid()
            self.btn_d_update.state(["disabled"])
            self.btn_d_delete.state(["disabled"])

    def new_adopter(self):
        self.tv_adopters.selection_remove(*self.tv_adopters.selection())
        self.sel_adopter_id = None
        self.ad_nombre.set(""); self.ad_doc.set(""); self.ad_tel.set("")
        self.ad_correo.set(""); self.ad_dir.set("")
        self._set_mode_adopter("new")

    def new_adoption(self):
        self.tv_adoptions.selection_remove(*self.tv_adoptions.selection())
        self.sel_adoption_id = None
        self.cmb_animal.set(""); self.cmb_adopter.set("")
        self.estado.set(ESTADOS[0])
        # IMPORTANT: DateEntry no acepta None -> limpiar borrando el entry
        try:
            self.egreso.entry.delete(0, "end")
        except Exception:
            pass
        self.obs.set("")
        self._set_mode_adoption("new")

    # ===================== Lookups / Tablas =====================
    def load_lookups(self):
        conn = get_conn(); cur = conn.cursor()

        # 🔹 Solo animales NO adoptados (ocultar aquí, mantener visibles en demás módulos/reportes)
        animals = cur.execute("""
            SELECT a.id, a.nombre
            FROM animals a
            WHERE NOT EXISTS (
                SELECT 1 FROM adoptions ad
                WHERE ad.animal_id = a.id
                  AND UPPER(ad.estado) = 'ADOPTADO'
            )
            ORDER BY a.nombre
        """).fetchall()

        adopters = cur.execute("SELECT id, nombre FROM adopters ORDER BY nombre").fetchall()

        self.cmb_animal["values"] = [f"{r['id']} - {r['nombre']}" for r in animals]
        self.cmb_adopter["values"] = [f"{r['id']} - {r['nombre']}" for r in adopters]

        conn.close()

    def load_tables(self):
        conn = get_conn(); cur = conn.cursor()

        rows = cur.execute("SELECT * FROM adopters ORDER BY id DESC").fetchall()
        self.tv_adopters.delete(*self.tv_adopters.get_children())
        for r in rows:
            self.tv_adopters.insert("", "end",
                                    values=(r["id"], r["nombre"], r["documento"], r["telefono"], r["correo"]))

        rows2 = cur.execute("""
            SELECT ad.id, a.nombre AS animal, ap.nombre AS adoptante, ad.estado, ad.fecha_egreso
            FROM adoptions ad
            JOIN animals a  ON a.id = ad.animal_id
            JOIN adopters ap ON ap.id = ad.adopter_id
            ORDER BY ad.id DESC
        """).fetchall()
        self.tv_adoptions.delete(*self.tv_adoptions.get_children())
        for r in rows2:
            self.tv_adoptions.insert("", "end",
                                     values=(r["id"], r["animal"], r["adoptante"], r["estado"], r["fecha_egreso"]))
        conn.close()

        paint_rows(self.tv_adopters)
        paint_rows(self.tv_adoptions)

    # ===================== Adoptantes CRUD =====================
    def on_select_adopter(self, _):
        sel = self.tv_adopters.selection()
        if not sel:
            return
        v = self.tv_adopters.item(sel[0], "values")
        self.sel_adopter_id = int(v[0])
        self.ad_nombre.set(v[1]); self.ad_doc.set(v[2]); self.ad_tel.set(v[3]); self.ad_correo.set(v[4])

        conn = get_conn(); cur = conn.cursor()
        r = cur.execute("SELECT COALESCE(direccion,'') d FROM adopters WHERE id=?", (self.sel_adopter_id,)).fetchone()
        conn.close()
        if r:
            self.ad_dir.set(r["d"])
        self._set_mode_adopter("edit")

    def save_adopter(self):
        if not self.ad_nombre.get().strip():
            messagebox.showwarning("Falta", "Nombre del adoptante requerido")
            return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO adopters(nombre, documento, telefono, correo, direccion)
            VALUES(?,?,?,?,?)
        """, (self.ad_nombre.get().strip(), self.ad_doc.get().strip(), self.ad_tel.get().strip(),
              self.ad_correo.get().strip(), self.ad_dir.get().strip()))
        conn.commit(); conn.close()
        self.new_adopter()
        self.load_lookups(); self.load_tables()

    def update_adopter(self):
        if not self.sel_adopter_id:
            return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            UPDATE adopters SET nombre=?, documento=?, telefono=?, correo=?, direccion=? WHERE id=?
        """, (self.ad_nombre.get().strip(), self.ad_doc.get().strip(), self.ad_tel.get().strip(),
              self.ad_correo.get().strip(), self.ad_dir.get().strip(), self.sel_adopter_id))
        conn.commit(); conn.close()
        self.new_adopter()
        self.load_lookups(); self.load_tables()

    def delete_adopter(self):
        if not self.sel_adopter_id:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar adoptante?"):
            return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM adopters WHERE id=?", (self.sel_adopter_id,))
        conn.commit(); conn.close()
        self.new_adopter()
        self.load_lookups(); self.load_tables()

    # ===================== Adopciones CRUD =====================
    def on_select_adoption(self, _):
        sel = self.tv_adoptions.selection()
        if not sel:
            return
        v = self.tv_adoptions.item(sel[0], "values")
        self.sel_adoption_id = int(v[0])
        self.estado.set(v[3])

        # Manejo seguro de fecha (puede ser None o '')
        try:
            self.egreso.set_date(v[4] or "")
        except Exception:
            self.egreso.entry.delete(0, "end")
            if v[4]:
                self.egreso.entry.insert(0, v[4])

        conn = get_conn(); cur = conn.cursor()
        r = cur.execute("""
            SELECT a.id AS aid, ap.id AS pid
            FROM adoptions ad
            JOIN animals a  ON a.id = ad.animal_id
            JOIN adopters ap ON ap.id = ad.adopter_id
            WHERE ad.id = ?
        """, (self.sel_adoption_id,)).fetchone()
        conn.close()
        if r:
            self.cmb_animal.set(self._fmt("animals", r["aid"]))
            self.cmb_adopter.set(self._fmt("adopters", r["pid"]))

        conn = get_conn(); cur = conn.cursor()
        r2 = cur.execute("SELECT COALESCE(observaciones,'') o FROM adoptions WHERE id=?",
                         (self.sel_adoption_id,)).fetchone()
        conn.close()
        if r2:
            self.obs.set(r2["o"])

        self._set_mode_adoption("edit")

    def _fmt(self, table, id_):
        conn = get_conn(); cur = conn.cursor()
        if table == "animals":
            n = cur.execute("SELECT nombre FROM animals WHERE id=?", (id_,)).fetchone()["nombre"]
        else:
            n = cur.execute("SELECT nombre FROM adopters WHERE id=?", (id_,)).fetchone()["nombre"]
        conn.close()
        return f"{id_} - {n}"

    def save_adoption(self):
        if not self.cmb_animal.get().strip() or not self.cmb_adopter.get().strip():
            messagebox.showwarning("Falta", "Seleccione animal y adoptante")
            return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO adoptions(animal_id, adopter_id, estado, fecha_egreso, observaciones)
            VALUES(?,?,?,?,?)
        """, (int(self.cmb_animal.get().split(" - ")[0]),
              int(self.cmb_adopter.get().split(" - ")[0]),
              self.estado.get(), self.egreso.entry.get().strip(), self.obs.get().strip()))
        conn.commit(); conn.close()
        self.new_adoption()
        self.load_tables()

    def update_adoption(self):
        if not self.sel_adoption_id:
            return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            UPDATE adoptions
               SET animal_id=?, adopter_id=?, estado=?, fecha_egreso=?, observaciones=?
             WHERE id=?
        """, (int(self.cmb_animal.get().split(" - ")[0]),
              int(self.cmb_adopter.get().split(" - ")[0]),
              self.estado.get(), self.egreso.entry.get().strip(), self.obs.get().strip(), self.sel_adoption_id))
        conn.commit(); conn.close()
        self.new_adoption()
        self.load_tables()

    def delete_adoption(self):
        if not self.sel_adoption_id:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar adopción?"):
            return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM adoptions WHERE id=?", (self.sel_adoption_id,))
        conn.commit(); conn.close()
        self.new_adoption()
        self.load_tables()

    # ===================== API público =====================
    def refresh(self):
        self.load_lookups()
        self.load_tables()
