import tkinter as tk
from reportlab.graphics.barcode import code128, eanbc, usps
from tkinter import ttk, messagebox, filedialog
from ttkbootstrap.widgets import DateEntry
from datetime import date
from db import get_conn
from ui.theme import zebra_fill, paint_rows
from ui.rounded import RoundedCard
from ui.pdf_utils import render_pdf_from_html

# progreso
import threading, queue

BTN_W = 14        # ancho homogéneo para botones de ANIMALES (verticales)
BTN_MIN_W_TYPES = 110  # ancho mínimo de cada botón en “Tipos de animal”


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


class AnimalsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.sel_type_id = None
        self.sel_animal_id = None

        # filtros
        self.q_nombre = tk.StringVar()
        self.q_sexo   = tk.StringVar(value="Todos")
        self.q_tipo   = tk.StringVar(value="Todos")

        self.build_ui()
        self.load_types()
        self.load_animals()
        self._set_type_mode("new")
        self._set_animal_mode("new")

    # ---------------- UI ----------------
    def build_ui(self):
        # --- Tarjeta: Tipos ---
        card_types = RoundedCard(self)
        card_types.grid(row=0, column=0, sticky="nsew", padx=(0,10), pady=(0,10))

        ttk.Label(card_types.body, text="Tipos de animal", font=("", 12, "bold"))\
            .grid(row=0, column=0, sticky="w", pady=(0,6))

        self.type_name = tk.StringVar()
        top = ttk.Frame(card_types.body, style="Card.TFrame")
        top.grid(row=1, column=0, sticky="ew", pady=(0,6))
        top.columnconfigure(0, weight=1)  # entrada
        # columnas 1..4: botones con mismo ancho (uniform) y minsize fijo
        for c in (1,2,3,4):
            top.columnconfigure(c, weight=1, uniform="typesbtns", minsize=BTN_MIN_W_TYPES)

        ttk.Entry(top, textvariable=self.type_name, width=20).grid(row=0, column=0, padx=(0,6), sticky="ew")

        self.btn_type_save   = ttk.Button(top, text="Guardar", style="Accent.TButton", command=self.add_type)
        self.btn_type_update = ttk.Button(top, text="Actualizar", command=self.update_type)
        self.btn_type_delete = ttk.Button(top, text="Eliminar", command=self.delete_type)
        self.btn_type_new    = ttk.Button(top, text="Nuevo", command=self.new_type)

        # IMPORTANTE: sticky="ew" para que el ancho lo defina la columna uniforme
        self.btn_type_save.grid(  row=0, column=1, padx=4, sticky="ew")
        self.btn_type_update.grid(row=0, column=2, padx=4, sticky="ew")
        self.btn_type_delete.grid(row=0, column=3, padx=4, sticky="ew")
        self.btn_type_new.grid(   row=0, column=4, padx=4, sticky="ew")

        ttk.Label(card_types.body, text="Lista de tipos", foreground="#64748B")\
            .grid(row=2, column=0, sticky="w", pady=(6,2))

        self.types_tv = ttk.Treeview(
            card_types.body, columns=("id","nombre"),
            show="headings", height=6, style="Modern.Treeview"
        )
        self.types_tv.heading("id", text="ID")
        self.types_tv.heading("nombre", text="Nombre")
        self.types_tv.column("id", width=40, anchor="center")
        self.types_tv.grid(row=3, column=0, sticky="nsew")
        self.types_tv.bind("<<TreeviewSelect>>", self.on_select_type)
        zebra_fill(self.types_tv)
        card_types.body.rowconfigure(3, weight=1)
        card_types.body.columnconfigure(0, weight=1)

        # --- Tarjeta: Animales ---
        card_anim = RoundedCard(self)
        card_anim.grid(row=0, column=1, sticky="nsew", pady=(0,10))

        ttk.Label(card_anim.body, text="Animales registrados", font=("", 12, "bold"))\
            .grid(row=0, column=0, sticky="w", pady=(0,6))

        # ===== Encabezado: formulario + acciones =====
        header_wrap = ttk.Frame(card_anim.body, style="Card.TFrame")
        header_wrap.grid(row=1, column=0, sticky="ew", pady=(0,6))
        header_wrap.columnconfigure(0, weight=1)                 # formulario flexible
        header_wrap.columnconfigure(1, weight=0, minsize=180)    # acciones ancho fijo

        # ---- Formulario (dos filas) ----
        form = ttk.Frame(header_wrap, style="Card.TFrame")
        form.grid(row=0, column=0, sticky="ew")

        # Fila 1: 5 columnas (Nombre, Sexo, Edad, Ingreso, Tipo)
        for c in range(5): form.columnconfigure(c, weight=1)
        form.grid_columnconfigure(3, weight=2, minsize=170)      # Ingreso (DateEntry) visible
        form.grid_columnconfigure(4, weight=1, minsize=160)      # Tipo con espacio suficiente

        ttk.Label(form, text="Nombre").grid(row=0, column=0, sticky="w", padx=(0,4))
        ttk.Label(form, text="Sexo").grid(row=0, column=1, sticky="w", padx=(0,4))
        ttk.Label(form, text="Edad (meses)").grid(row=0, column=2, sticky="w", padx=(0,4))
        ttk.Label(form, text="Ingreso").grid(row=0, column=3, sticky="w", padx=(0,4))
        ttk.Label(form, text="Tipo").grid(row=0, column=4, sticky="w", padx=(0,4))

        self.an_nombre = tk.StringVar()
        self.an_sexo   = tk.StringVar()
        self.an_edad   = tk.IntVar(value=0)
        self.an_notas  = tk.StringVar()

        ttk.Entry(form, textvariable=self.an_nombre).grid(row=1, column=0, sticky="ew", padx=(0,8))
        ttk.Combobox(form, textvariable=self.an_sexo, values=["Macho","Hembra","ND"], state="readonly")\
            .grid(row=1, column=1, sticky="ew", padx=(0,8))
        ttk.Entry(form, textvariable=self.an_edad).grid(row=1, column=2, sticky="ew", padx=(0,8))
        self.ent_ingreso = DateEntry(form, bootstyle="info", dateformat="%Y-%m-%d", width=12)
        self.ent_ingreso.grid(row=1, column=3, sticky="ew", padx=(0,8))
        self.cmb_tipo  = ttk.Combobox(form, state="readonly")
        self.cmb_tipo.grid(row=1, column=4, sticky="ew", padx=(0,12))  # margen derecho para que no se vea “pegado”

        # Fila 2: Notas ocupa TODO el ancho
        ttk.Label(form, text="Notas").grid(row=2, column=0, sticky="w", padx=(0,4), pady=(8,0))
        ttk.Entry(form, textvariable=self.an_notas)\
            .grid(row=3, column=0, columnspan=5, sticky="ew")

        # ---- Acciones a la derecha (mismos tamaños) ----
        actions = ttk.Frame(header_wrap)
        actions.grid(row=0, column=1, sticky="ne")
        self.btn_an_save   = ttk.Button(actions, text="Guardar", style="Accent.TButton", command=self.add_animal, width=BTN_W)
        self.btn_an_update = ttk.Button(actions, text="Actualizar", command=self.update_animal, width=BTN_W)
        self.btn_an_delete = ttk.Button(actions, text="Eliminar", command=self.delete_animal, width=BTN_W)
        self.btn_an_pdf    = ttk.Button(actions, text="Historial PDF", command=self.export_profile_pdf, width=BTN_W)
        self.btn_an_new    = ttk.Button(actions, text="Nuevo", command=self.new_animal, width=BTN_W)
        for i, b in enumerate([self.btn_an_save, self.btn_an_update, self.btn_an_delete, self.btn_an_pdf, self.btn_an_new]):
            b.grid(row=i, column=0, padx=4, pady=2, sticky="ew")

        ttk.Separator(card_anim.body, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(2,6))

        # ===== Filtros =====
        filters = ttk.Frame(card_anim.body, style="Card.TFrame")
        filters.grid(row=3, column=0, sticky="ew", pady=(0,6))
        for c in range(6): filters.columnconfigure(c, weight=1)

        ttk.Label(filters, text="Buscar").grid(row=0, column=0, sticky="w", padx=(0,4))
        self.ent_q = ttk.Entry(filters, textvariable=self.q_nombre)
        self.ent_q.grid(row=1, column=0, sticky="ew", padx=(0,8))
        self.ent_q.bind("<Return>", lambda _: self.apply_filters())

        ttk.Label(filters, text="Tipo").grid(row=0, column=1, sticky="w", padx=(0,4))
        self.cmb_q_tipo = ttk.Combobox(filters, textvariable=self.q_tipo, state="readonly")
        self.cmb_q_tipo.grid(row=1, column=1, sticky="ew", padx=(0,8))

        ttk.Label(filters, text="Sexo").grid(row=0, column=2, sticky="w", padx=(0,4))
        self.cmb_q_sexo = ttk.Combobox(filters, textvariable=self.q_sexo,
                                       values=["Todos","M","F","ND"], state="readonly")
        self.cmb_q_sexo.grid(row=1, column=2, sticky="ew", padx=(0,8))

        btns = ttk.Frame(filters)
        btns.grid(row=1, column=3, columnspan=2, sticky="w")
        ttk.Button(btns, text="Buscar", command=self.apply_filters).grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="Limpiar", command=self.clear_filters).grid(row=0, column=1, padx=4)

        self.lbl_count = ttk.Label(filters, text="", foreground="#64748B")
        self.lbl_count.grid(row=1, column=5, sticky="e")

        # ===== Tabla =====
        ttk.Label(card_anim.body, text="Lista de animales", foreground="#64748B")\
            .grid(row=4, column=0, sticky="w", pady=(6,2))

        self.anim_tv = ttk.Treeview(
            card_anim.body,
            columns=("id","nombre","tipo","sexo","edad","ingreso"),
            show="headings", height=12, style="Modern.Treeview"
        )
        for c,t in [("id","ID"),("nombre","Nombre"),("tipo","Tipo"),
                    ("sexo","Sexo"),("edad","Edad(m)"),("ingreso","Ingreso")]:
            self.anim_tv.heading(c, text=t)
        self.anim_tv.column("id", width=60, anchor="center")
        self.anim_tv.grid(row=5, column=0, sticky="nsew")
        self.anim_tv.bind("<<TreeviewSelect>>", self.on_select_animal)
        zebra_fill(self.anim_tv)

        card_anim.body.rowconfigure(5, weight=1)
        card_anim.body.columnconfigure(0, weight=1)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)

    # ---------------- Helper progreso ----------------
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

    # ---------------- Modo botones ----------------
    def _set_type_mode(self, mode: str):
        if mode == "edit":
            self.btn_type_save.grid_remove()
            self.btn_type_update.state(["!disabled"])
            self.btn_type_delete.state(["!disabled"])
        else:
            if not self.btn_type_save.winfo_ismapped():
                self.btn_type_save.grid()
            self.btn_type_update.state(["disabled"])
            self.btn_type_delete.state(["disabled"])

    def _set_animal_mode(self, mode: str):
        if mode == "edit":
            self.btn_an_save.grid_remove()
            self.btn_an_update.state(["!disabled"])
            self.btn_an_delete.state(["!disabled"])
        else:
            if not self.btn_an_save.winfo_ismapped():
                self.btn_an_save.grid()
            self.btn_an_update.state(["disabled"])
            self.btn_an_delete.state(["disabled"])

    # ---------------- Tipos ----------------
    def load_types(self):
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute("SELECT id, nombre FROM animal_types ORDER BY nombre").fetchall()

        self.types_tv.delete(*self.types_tv.get_children())
        self.cmb_tipo["values"] = [f"{r['id']} - {r['nombre']}" for r in rows]
        for r in rows:
            self.types_tv.insert("", "end", values=(r["id"], r["nombre"]))

        self.cmb_q_tipo["values"] = ["Todos"] + [f"{r['id']} - {r['nombre']}" for r in rows]
        if self.q_tipo.get() not in self.cmb_q_tipo["values"]:
            self.q_tipo.set("Todos")

        conn.close()
        paint_rows(self.types_tv)

    def on_select_type(self, _):
        sel = self.types_tv.selection()
        if not sel: return
        vals = self.types_tv.item(sel[0], "values")
        self.sel_type_id = int(vals[0])
        self.type_name.set(vals[1])
        self._set_type_mode("edit")

    def new_type(self):
        self.types_tv.selection_remove(*self.types_tv.selection())
        self.sel_type_id = None
        self.type_name.set("")
        self._set_type_mode("new")

    def add_type(self):
        name = self.type_name.get().strip()
        if not name: return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("INSERT INTO animal_types(nombre) VALUES(?)", (name,))
        conn.commit(); conn.close()
        self.new_type()
        self.load_types()

    def update_type(self):
        if not self.sel_type_id: return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE animal_types SET nombre=? WHERE id=?", (self.type_name.get().strip(), self.sel_type_id))
        conn.commit(); conn.close()
        self.new_type()
        self.load_types()

    def delete_type(self):
        if not self.sel_type_id: return
        if not messagebox.askyesno("Eliminar", "¿Eliminar tipo seleccionado?"): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM animal_types WHERE id=?", (self.sel_type_id,))
        conn.commit(); conn.close()
        self.new_type()
        self.load_types()

    # ---------------- Filtros / listado ----------------
    def _build_filters_sql(self):
        clauses, params = [], []
        if self.q_nombre.get().strip():
            clauses.append("a.nombre LIKE ?")
            params.append("%" + self.q_nombre.get().strip() + "%")
        if self.q_sexo.get() != "Todos":
            clauses.append("a.sexo = ?")
            params.append(self.q_sexo.get())
        if self.q_tipo.get() != "Todos":
            tipo_id = int(self.q_tipo.get().split(" - ")[0])
            clauses.append("a.especie_id = ?")
            params.append(tipo_id)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        return where, params

    def load_animals(self):
        where, params = self._build_filters_sql()
        conn = get_conn(); cur = conn.cursor()
        rows = cur.execute(f"""
            SELECT a.id, a.nombre, t.nombre as tipo, a.sexo, a.edad_meses, a.ingreso_fecha
            FROM animals a JOIN animal_types t ON t.id=a.especie_id
            {where}
            ORDER BY a.id DESC
        """, params).fetchall()
        self.anim_tv.delete(*self.anim_tv.get_children())
        for r in rows:
            self.anim_tv.insert("", "end",
                                values=(r["id"], r["nombre"], r["tipo"], r["sexo"], r["edad_meses"], r["ingreso_fecha"]))
        conn.close()
        paint_rows(self.anim_tv)
        self.lbl_count.config(text=f"{len(rows)} resultado(s)")

    def apply_filters(self):
        self.load_animals()

    def clear_filters(self):
        self.q_nombre.set(""); self.q_sexo.set("Todos"); self.q_tipo.set("Todos")
        self.load_animals()

    # ---------------- Selección / CRUD ----------------
    def on_select_animal(self, _):
        sel = self.anim_tv.selection()
        if not sel: return
        vals = self.anim_tv.item(sel[0], "values")
        self.sel_animal_id = int(vals[0])
        self.an_nombre.set(vals[1]); self.an_sexo.set(vals[3]); self.an_edad.set(vals[4])
        try:
            self.ent_ingreso.set_date(vals[5])
        except Exception:
            self.ent_ingreso.entry.delete(0, "end")
            if vals[5]:
                self.ent_ingreso.entry.insert(0, vals[5])

        conn = get_conn(); cur = conn.cursor()
        r = cur.execute("SELECT t.id FROM animals a JOIN animal_types t ON t.id=a.especie_id WHERE a.id=?",
                        (self.sel_animal_id,)).fetchone()
        conn.close()
        if r: self.cmb_tipo.set(f"{r['id']} - {vals[2]}")
        self._set_animal_mode("edit")

    def new_animal(self):
        self.anim_tv.selection_remove(*self.anim_tv.selection())
        self.sel_animal_id = None
        self.an_nombre.set(""); self.an_sexo.set(""); self.an_edad.set(0); self.an_notas.set("")
        self.ent_ingreso.set_date(date.today())
        self.cmb_tipo.set("")
        self._set_animal_mode("new")

    def add_animal(self):
        if not self.an_nombre.get().strip() or not self.cmb_tipo.get():
            messagebox.showwarning("Falta", "Nombre y Tipo son obligatorios"); return
        type_id = int(self.cmb_tipo.get().split(" - ")[0])
        ingreso = self.ent_ingreso.entry.get().strip()
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO animals(nombre, especie_id, sexo, edad_meses, ingreso_fecha, notas)
            VALUES(?,?,?,?,?,?)
        """, (self.an_nombre.get().strip(), type_id, self.an_sexo.get(), int(self.an_edad.get() or 0),
              ingreso, self.an_notas.get().strip()))
        conn.commit(); conn.close()
        self.new_animal()
        self.load_animals()

    def update_animal(self):
        if not self.sel_animal_id: return
        type_id = int(self.cmb_tipo.get().split(" - ")[0])
        ingreso = self.ent_ingreso.entry.get().strip()
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            UPDATE animals SET nombre=?, especie_id=?, sexo=?, edad_meses=?, ingreso_fecha=?, notas=? WHERE id=?
        """, (self.an_nombre.get().strip(), type_id, self.an_sexo.get(), int(self.an_edad.get() or 0),
              ingreso, self.an_notas.get().strip(), self.sel_animal_id))
        conn.commit(); conn.close()
        self.new_animal()
        self.load_animals()

    def delete_animal(self):
        if not self.sel_animal_id: return
        if not messagebox.askyesno("Eliminar", "¿Eliminar animal seleccionado?"): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM animals WHERE id=?", (self.sel_animal_id,))
        conn.commit(); conn.close()
        self.new_animal()
        self.load_animals()

    # ======= FICHA PDF =======
    def export_profile_pdf(self):
        if not self.sel_animal_id:
            messagebox.showwarning("Ficha", "Selecciona un animal en la lista"); return

        conn = get_conn(); cur = conn.cursor()

        # === Datos base del animal
        animal = cur.execute("""
            SELECT a.id, a.nombre, t.nombre AS tipo, a.sexo, a.edad_meses, a.ingreso_fecha,
                COALESCE(a.notas,'') AS notas
            FROM animals a
            JOIN animal_types t ON t.id=a.especie_id
            WHERE a.id=?
        """, (self.sel_animal_id,)).fetchone()

        # === Listados
        vaccines = cur.execute("""
            SELECT vacuna, fecha_aplicacion,
                COALESCE(proxima_fecha,'') AS proxima,
                COALESCE(notas,'') AS notas
            FROM vaccines
            WHERE animal_id=?
            ORDER BY fecha_aplicacion DESC
        """, (self.sel_animal_id,)).fetchall()

        deworms = cur.execute("""
            SELECT producto, fecha_aplicacion,
                COALESCE(proxima_fecha,'') AS proxima,
                COALESCE(notas,'') AS notas
            FROM dewormings
            WHERE animal_id=?
            ORDER BY fecha_aplicacion DESC
        """, (self.sel_animal_id,)).fetchall()

        donations = cur.execute("""
            SELECT d.fecha, s.nombre AS padrino, d.monto,
                COALESCE(d.metodo,'') AS metodo,
                COALESCE(d.nota,'')   AS nota
            FROM donations d
            JOIN sponsors s ON s.id=d.sponsor_id
            WHERE d.animal_id=?
            ORDER BY d.fecha DESC
        """, (self.sel_animal_id,)).fetchall()

        # === Última adopción (define estado ejecutivo)
        adoption = cur.execute("""
            SELECT ad.estado,
                COALESCE(ad.fecha_egreso,'') AS fecha_egreso,
                COALESCE(ad.observaciones,'') AS obs,
                ap.nombre AS adoptante
            FROM adoptions ad
            JOIN adopters ap ON ap.id = ad.adopter_id
            WHERE ad.animal_id=?
            ORDER BY ad.id DESC
            LIMIT 1
        """, (self.sel_animal_id,)).fetchone()
        conn.close()

        # --- Helpers
        def money(x):
            try:
                v = float(x or 0.0)
                return f"{v:,.0f}".replace(",", ".")
            except Exception:
                return str(x or "0")

        total_don = sum([float(r["monto"] or 0) for r in donations]) if donations else 0.0
        vacunas_cnt = len(vaccines)
        deworm_cnt  = len(deworms)

        # === Estado ejecutivo (badge + color)
        # Regla:
        # - Si existe adopción y estado == 'ADOPTADO'  -> ADOPTADO (verde)
        # - Si existe adopción y estado != 'ADOPTADO'  -> EN PROCESO (ámbar)
        # - Si no hay adopción                           -> EN ALBERGUE (azul)
        if adoption and (adoption["estado"] or "").upper() == "ADOPTADO":
            estado_txt, estado_col = "ADOPTADO", "#16a34a"
        elif adoption:
            estado_txt, estado_col = "EN PROCESO", "#f59e0b"
        else:
            estado_txt, estado_col = "EN ALBERGUE", "#2563eb"

        # === Archivo sugerido
        from datetime import date
        today = date.today().isoformat()
        default_name = f"ficha_{(animal['nombre'] or '').replace(' ','_')}_{animal['id']}_{today}.pdf"

        # === Marca (logo si existe)
        import os
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"))
        has_logo = os.path.exists(logo_path)
        logo_tag = f"<img src='file://{logo_path}' style='height:34px'>" if has_logo else "<strong>AlbergueApp</strong>"

        # === HTML Ejecutivo (sin info repetida)
        #   - Chips: Sexo / Edad / Ingreso
        #   - Datos generales: solo Tipo + Notas
        #   - Situación actual: estado/adoptante/egreso/obs (compacto)
        #   - Donaciones: total + tabla (máx 10)
        #   - Vacunas / Desparas: con contadores
        limit_don = 10  # mostramos como máximo 10 en la tabla

        def tr_safe(val):  # texto vacío en raya
            return val if (val not in (None, "")) else "—"

        html = f"""<!DOCTYPE html><html lang="es"><meta charset="utf-8">
    <style>
    @page {{ size:A4; margin: 18mm 16mm; }}
    body {{ font-family:'Segoe UI', Arial, sans-serif; color:#0f172a; }}
    h1 {{ margin:0; font-size:20pt; }}
    h2 {{ margin:0 0 6px; font-size:12.5pt; color:#334155; }}
    .small {{ font-size:9pt; }} .muted {{ color:#64748B; }}

    .header {{
    display:flex; justify-content:space-between; align-items:center;
    border-bottom:1px solid #E5E7EB; padding-bottom:6mm; margin-bottom:8mm;
    }}
    .badge {{
    display:inline-block; background:{estado_col}; color:#fff; font-weight:700;
    padding:4px 12px; border-radius:999px; font-size:10.5pt; letter-spacing:.2px;
    }}

    .kchips {{ display:flex; gap:8px; margin-top:6px; flex-wrap:wrap; }}
    .chip {{
    display:inline-block; background:#F1F5F9; border:1px solid #E5E7EB;
    padding:4px 10px; border-radius:999px; font-size:9.5pt;
    }}

    .grid2 {{ display:grid; grid-template-columns:1.1fr 0.9fr; gap:9mm; }}
    .card {{
    border:1px solid #E5EAF2; border-radius:10px; padding:7mm; background:#fff;
    }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ border:1px solid #E5EAF2; padding:6px 8px; font-size:10pt; }}
    th {{ background:#F2F6FB; text-align:left; }}

    .zebra tr:nth-child(even) td {{ background:#fafbff; }}

    .section-title {{
    font-variant:all-small-caps; letter-spacing:.8px; color:#475569;
    font-weight:700; margin:10mm 0 4mm;
    }}

    .kv table {{ border:0; }}
    .kv th,.kv td {{ border:0; padding:3px 0; }}
    .kv th {{ width:35%; color:#64748B; background:transparent; }}

    .footer {{ margin-top:10mm; text-align:center; }}
    </style>
    <body>

    <div class="header">
    <div style="display:flex; gap:10px; align-items:center;">{logo_tag}
        <div style="margin-left:8px">
        <div class="small muted">Ficha del animal</div>
        <h1>{tr_safe(animal['nombre'])}</h1>
        <div class="muted small">ID #{animal['id']} · {tr_safe(animal['tipo'])}</div>
        <div class="kchips">
            <span class="chip">Sexo: {tr_safe(animal['sexo'])}</span>
            <span class="chip">Edad: {tr_safe(animal['edad_meses'])} meses</span>
            <span class="chip">Ingreso: {tr_safe(animal['ingreso_fecha'])}</span>
        </div>
        </div>
    </div>
    <div class="badge">{estado_txt}</div>
    </div>

    <div class="grid2">
    <div class="card">
        <h2>Datos generales</h2>
        <div class="kv">
        <table>
            <tr><th>Tipo</th><td>{tr_safe(animal['tipo'])}</td></tr>
            <tr><th>Notas</th><td>{tr_safe(animal['notas'])}</td></tr>
        </table>
        </div>
    </div>

    <div class="card">
        <h2>Situación actual</h2>
        <table>
        <tr><th>Estado</th><td>{estado_txt}</td></tr>
        <tr><th>Adoptante</th><td>{tr_safe(adoption['adoptante'] if adoption else '')}</td></tr>
        <tr><th>Fecha de egreso</th><td>{tr_safe(adoption['fecha_egreso'] if adoption else '')}</td></tr>
        <tr><th>Observaciones</th><td>{tr_safe(adoption['obs'] if adoption else '')}</td></tr>
        </table>
    </div>
    </div>

    <div class="section-title">Historial sanitario</div>
    <div class="grid2">
    <div class="card">
        <h2>Vacunas ({vacunas_cnt})</h2>
        <table class="zebra">
        <tr><th>Vacuna</th><th>Aplicación</th><th>Próxima</th><th>Notas</th></tr>
        {''.join([f"<tr><td>{tr_safe(v['vacuna'])}</td><td>{tr_safe(v['fecha_aplicacion'])}</td><td>{tr_safe(v['proxima'])}</td><td>{tr_safe(v['notas'])}</td></tr>" for v in vaccines]) or "<tr><td colspan='4' class='small muted'>Sin registros</td></tr>"}
        </table>
    </div>

    <div class="card">
        <h2>Desparasitaciones ({deworm_cnt})</h2>
        <table class="zebra">
        <tr><th>Producto</th><th>Aplicación</th><th>Próxima</th><th>Notas</th></tr>
        {''.join([f"<tr><td>{tr_safe(d['producto'])}</td><td>{tr_safe(d['fecha_aplicacion'])}</td><td>{tr_safe(d['proxima'])}</td><td>{tr_safe(d['notas'])}</td></tr>" for d in deworms]) or "<tr><td colspan='4' class='small muted'>Sin registros</td></tr>"}
        </table>
    </div>
    </div>

    <div class="section-title">Apoyo económico</div>
    <div class="card">
    <div class="small muted" style="margin-bottom:6px">Total donado a este animal</div>
    <div style="font-size:18pt; font-weight:800; margin-bottom:8px">{money(total_don)}</div>

    <table class="zebra">
        <tr><th>Fecha</th><th>Padrino</th><th>Monto</th><th>Método</th><th>Nota</th></tr>
        {''.join([f"<tr><td>{tr_safe(d['fecha'])}</td><td>{tr_safe(d['padrino'])}</td><td>{money(d['monto'])}</td><td>{tr_safe(d['metodo'])}</td><td>{tr_safe(d['nota'])}</td></tr>" for d in donations[:limit_don]]) or "<tr><td colspan='5' class='small muted'>Sin registros</td></tr>"}
    </table>
    {"<div class='small muted' style='margin-top:6px'>Mostrando las últimas " + str(limit_don) + " donaciones</div>" if len(donations) > limit_don else ""}
    </div>

    <div class="footer small muted">Generado por AlbergueApp · {today}</div>

    </body></html>"""

                # Guardar
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name,
            title="Guardar ficha PDF"
        )
        if not path:
            return

        # === Ejecutar render en segundo plano con barra ===
        def _worker():
            ok = render_pdf_from_html(html, path)
            if not ok:
                # si no fue OK, levantamos excepción para que _run_with_busy muestre error
                raise RuntimeError("No fue posible generar el PDF.")

        self._run_with_busy(
            "Generando ficha PDF…",
            _worker,
            f"Ficha generada:\n{path}"
        )
