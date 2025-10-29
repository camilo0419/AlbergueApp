import tkinter as tk
from tkinter import ttk, messagebox
from sqlite3 import OperationalError
from ui.rounded import RoundedCard
from ui.theme import zebra_fill, paint_rows
from db import get_conn

BTN_W = 14  # ancho uniforme para botones del bloque de acciones


class SponsorsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.sel_id = None

        # filtros
        self.q_text = tk.StringVar()

        # === asegura esquema ===
        self._ensure_schema()

        self._build_ui()
        self.load_sponsors()
        self._set_mode("new")

    # ---------- esquema ----------
    def _ensure_schema(self):
        """Si sponsors no tiene 'notas', la agrega."""
        conn = get_conn(); cur = conn.cursor()
        cols = cur.execute("PRAGMA table_info(sponsors)").fetchall()
        colnames = [c["name"] for c in cols]  # row_factory=sqlite3.Row
        if "notas" not in colnames:
            cur.execute("ALTER TABLE sponsors ADD COLUMN notas TEXT")
            conn.commit()
        conn.close()

    # ---------- UI ----------
    def _build_ui(self):
        # Tarjeta principal
        card = RoundedCard(self)
        card.grid(row=0, column=0, sticky="nsew")

        ttk.Label(card.body, text="Padrinos registrados", font=("", 12, "bold"))\
            .grid(row=0, column=0, sticky="w", pady=(0,6))

        # Formulario + Acciones (mismo layout que Animales)
        header_wrap = ttk.Frame(card.body, style="Card.TFrame")
        header_wrap.grid(row=1, column=0, sticky="ew", pady=(0,6))
        header_wrap.columnconfigure(0, weight=1)              # formulario
        header_wrap.columnconfigure(1, weight=0, minsize=180) # acciones

        # ----- Formulario -----
        form = ttk.Frame(header_wrap, style="Card.TFrame")
        form.grid(row=0, column=0, sticky="ew")

        for c in range(3):
            form.columnconfigure(c, weight=1)

        ttk.Label(form, text="Nombre").grid(row=0, column=0, sticky="w", padx=(0,4))
        ttk.Label(form, text="Teléfono").grid(row=0, column=1, sticky="w", padx=(0,4))
        ttk.Label(form, text="Correo").grid(row=0, column=2, sticky="w", padx=(0,4))

        self.sp_nombre = tk.StringVar()
        self.sp_tel    = tk.StringVar()
        self.sp_mail   = tk.StringVar()
        self.sp_notas  = tk.StringVar()

        ttk.Entry(form, textvariable=self.sp_nombre).grid(row=1, column=0, sticky="ew", padx=(0,8))
        ttk.Entry(form, textvariable=self.sp_tel).grid(row=1, column=1, sticky="ew", padx=(0,8))
        ttk.Entry(form, textvariable=self.sp_mail).grid(row=1, column=2, sticky="ew", padx=(0,0))

        ttk.Label(form, text="Notas").grid(row=2, column=0, sticky="w", padx=(0,4), pady=(8,0))
        ttk.Entry(form, textvariable=self.sp_notas).grid(row=3, column=0, columnspan=3, sticky="ew")

        # ----- Acciones -----
        actions = ttk.Frame(header_wrap)
        actions.grid(row=0, column=1, sticky="ne")
        self.btn_save   = ttk.Button(actions, text="Guardar", style="Accent.TButton", command=self.add_sponsor, width=BTN_W)
        self.btn_update = ttk.Button(actions, text="Actualizar", command=self.update_sponsor, width=BTN_W)
        self.btn_delete = ttk.Button(actions, text="Eliminar", command=self.delete_sponsor, width=BTN_W)
        self.btn_new    = ttk.Button(actions, text="Nuevo", command=self.new_sponsor, width=BTN_W)
        for i, b in enumerate([self.btn_save, self.btn_update, self.btn_delete, self.btn_new]):
            b.grid(row=i, column=0, padx=4, pady=2, sticky="ew")

        ttk.Separator(card.body, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(2,6))

        # ----- Filtros -----
        filters = ttk.Frame(card.body, style="Card.TFrame")
        filters.grid(row=3, column=0, sticky="ew", pady=(0,6))
        for c in range(3):
            filters.columnconfigure(c, weight=1)

        ttk.Label(filters, text="Buscar").grid(row=0, column=0, sticky="w", padx=(0,4))
        ent_q = ttk.Entry(filters, textvariable=self.q_text)
        ent_q.grid(row=1, column=0, sticky="ew", padx=(0,8))
        ent_q.bind("<Return>", lambda _: self.apply_filters())

        btns = ttk.Frame(filters)
        btns.grid(row=1, column=1, sticky="w")
        ttk.Button(btns, text="Buscar", command=self.apply_filters).grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="Limpiar", command=self.clear_filters).grid(row=0, column=1, padx=4)

        self.lbl_count = ttk.Label(filters, text="", foreground="#64748B")
        self.lbl_count.grid(row=1, column=2, sticky="e")

        # ----- Tabla -----
        self.tv = ttk.Treeview(
            card.body,
            columns=("id","nombre","telefono","correo"),
            show="headings", height=16, style="Modern.Treeview"
        )
        for c,t in [("id","ID"),("nombre","Nombre"),("telefono","Teléfono"),("correo","Correo")]:
            self.tv.heading(c, text=t)
        self.tv.column("id", width=60, anchor="center")
        self.tv.grid(row=4, column=0, sticky="nsew")
        self.tv.bind("<<TreeviewSelect>>", self.on_select)
        zebra_fill(self.tv)

        # layout
        card.body.rowconfigure(4, weight=1)
        card.body.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    # ---------- Modo botones ----------
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

    def new_sponsor(self):
        self.tv.selection_remove(*self.tv.selection())
        self.sel_id = None
        self.sp_nombre.set(""); self.sp_tel.set(""); self.sp_mail.set(""); self.sp_notas.set("")
        self._set_mode("new")

    # ---------- Datos / CRUD ----------
    def _build_where(self):
        clauses, params = [], []
        q = self.q_text.get().strip()
        if q:
            clauses.append("(nombre LIKE ? OR telefono LIKE ? OR correo LIKE ?)")
            like = f"%{q}%"
            params += [like, like, like]
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        return where, params

    def load_sponsors(self):
        where, params = self._build_where()
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute(f"""
            SELECT id, nombre, COALESCE(telefono,'') AS telefono, COALESCE(correo,'') AS correo
            FROM sponsors
            {where}
            ORDER BY id DESC
        """, params).fetchall()
        self.tv.delete(*self.tv.get_children())
        for r in rows:
            self.tv.insert("", "end", values=(r["id"], r["nombre"], r["telefono"], r["correo"]))
        conn.close()
        paint_rows(self.tv)
        self.lbl_count.config(text=f"{len(rows)} resultado(s)")

    def apply_filters(self):
        self.load_sponsors()

    def clear_filters(self):
        self.q_text.set("")
        self.load_sponsors()

    def on_select(self, _):
        sel = self.tv.selection()
        if not sel: return
        vals = self.tv.item(sel[0], "values")
        self.sel_id = int(vals[0])
        self.sp_nombre.set(vals[1]); self.sp_tel.set(vals[2]); self.sp_mail.set(vals[3])

        # traer notas si existen (tolerante a esquema)
        try:
            conn = get_conn(); cur = conn.cursor()
            r = cur.execute("SELECT COALESCE(notas,'') notas FROM sponsors WHERE id=?", (self.sel_id,)).fetchone()
            conn.close()
            self.sp_notas.set(r["notas"] if r else "")
        except OperationalError:
            # por si la DB antigua no tenía la columna
            self.sp_notas.set("")

        self._set_mode("edit")

    def add_sponsor(self):
        if not self.sp_nombre.get().strip():
            messagebox.showwarning("Falta", "El nombre es obligatorio"); return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO sponsors(nombre, telefono, correo, notas)
            VALUES(?,?,?,?)
        """, (self.sp_nombre.get().strip(), self.sp_tel.get().strip(),
              self.sp_mail.get().strip(), self.sp_notas.get().strip()))
        conn.commit(); conn.close()
        self.new_sponsor()
        self.load_sponsors()

    def update_sponsor(self):
        if not self.sel_id: return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            UPDATE sponsors
            SET nombre=?, telefono=?, correo=?, notas=?
            WHERE id=?
        """, (self.sp_nombre.get().strip(), self.sp_tel.get().strip(),
              self.sp_mail.get().strip(), self.sp_notas.get().strip(), self.sel_id))
        conn.commit(); conn.close()
        self.new_sponsor()
        self.load_sponsors()

    def delete_sponsor(self):
        if not self.sel_id: return
        if not messagebox.askyesno("Eliminar", "¿Eliminar padrino seleccionado?"): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM sponsors WHERE id=?", (self.sel_id,))
        conn.commit(); conn.close()
        self.new_sponsor()
        self.load_sponsors()

    # ---------- API público ----------
    def refresh(self):
        self.load_sponsors()
