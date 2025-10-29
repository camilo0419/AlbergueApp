import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta, datetime
from ui.rounded import RoundedCard
from ui.theme import zebra_fill, paint_rows
from db import get_conn

# Gráficos (opcional)
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.ticker import MaxNLocator
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False


class DashboardFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self._build_ui()
        self.refresh()

    # ---------- UI ----------
    def _build_ui(self):
        # ===== KPIs (4 tarjetas) =====
        self.kpi_wrap = ttk.Frame(self)
        self.kpi_wrap.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for c in range(4):
            self.kpi_wrap.columnconfigure(c, weight=1)

        self.kpi_cards = []
        self.kpi_values = []
        kpi_titles = ["Animales", "Padrinos", "Donaciones (mes)", "Adopciones"]
        for i, title in enumerate(kpi_titles):
            card = RoundedCard(self.kpi_wrap)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            body = card.body
            # centrado horizontal y vertical
            body.columnconfigure(0, weight=1)
            body.rowconfigure(0, weight=1)
            body.rowconfigure(3, weight=1)

            title_lbl = ttk.Label(body, text=title, foreground="#64748B", anchor="center", justify="center")
            title_lbl.grid(row=1, column=0, sticky="ew")
            val = ttk.Label(body, text="—", font=("Segoe UI", 24, "bold"), anchor="center", justify="center")
            val.grid(row=2, column=0, sticky="ew", pady=(2, 0))
            sub = ttk.Label(body, text="", foreground="#64748B", anchor="center", justify="center")
            sub.grid(row=3, column=0, sticky="n")

            self.kpi_cards.append((card, sub))
            self.kpi_values.append(val)

        # ===== Panel inferior: Pendientes (izq) + Gráficos (der) =====
        # Pendientes
        self.pending_card = RoundedCard(self)
        self.pending_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        head = ttk.Frame(self.pending_card.body)
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="Pendientes de Salud (30 días)", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.pending_card.body.rowconfigure(1, weight=1)
        self.pending_card.body.columnconfigure(0, weight=1)

        self.tv_pending = ttk.Treeview(
            self.pending_card.body,
            columns=("tipo", "animal", "proxima", "dias"),
            show="headings",
            height=12,
            style="Modern.Treeview",
        )
        for c, t in [("tipo", "Tipo"), ("animal", "Animal"), ("proxima", "Próxima"), ("dias", "Días")]:
            self.tv_pending.heading(c, text=t)
        self.tv_pending.column("tipo", width=120, anchor="w")
        self.tv_pending.column("animal", width=180, anchor="w")
        self.tv_pending.column("proxima", width=110, anchor="center")
        self.tv_pending.column("dias", width=60, anchor="e")
        self.tv_pending.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        zebra_fill(self.tv_pending)

        # Leyenda (solo próximos; no mostramos vencidos)
        legend = ttk.Frame(self.pending_card.body)
        legend.grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(legend, text="●", foreground="#CA8A04").grid(row=0, column=0, padx=(0, 4))
        ttk.Label(legend, text="Próximo (≤7 días)", foreground="#64748B").grid(row=0, column=1, padx=(0, 12))
        ttk.Label(legend, text="●", foreground="#94A3B8").grid(row=0, column=2, padx=(0, 4))
        ttk.Label(legend, text="Dentro de 8–30 días", foreground="#64748B").grid(row=0, column=3)

        # Gráficos
        self.chart_card = RoundedCard(self)
        self.chart_card.grid(row=1, column=1, sticky="nsew")
        self.chart_card.body.rowconfigure(0, weight=1)
        self.chart_card.body.columnconfigure(0, weight=1)

        if MATPLOTLIB_OK:
            # más alto y con layout automático para evitar solapes
            self.fig = Figure(figsize=(6.4, 5.4), dpi=100, constrained_layout=True)
            self.ax1 = self.fig.add_subplot(211)  # donaciones
            self.ax2 = self.fig.add_subplot(212)  # tipos
            self.fig.subplots_adjust(hspace=0.35)  # espacio entre subplots

            self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_card.body)
            self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        else:
            ttk.Label(
                self.chart_card.body,
                text="Instala matplotlib para ver gráficos (pip install matplotlib)",
                foreground="#64748B",
            ).grid(row=0, column=0, padx=10, pady=10)

        # layout root
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    # ---------- Datos ----------
    def _kpis(self):
        conn = get_conn()
        cur = conn.cursor()
        total_anim = cur.execute("SELECT COUNT(*) c FROM animals").fetchone()["c"]
        total_pads = cur.execute("SELECT COUNT(*) c FROM sponsors").fetchone()["c"]
        first = date.today().replace(day=1).isoformat()
        don_mes = cur.execute("SELECT COALESCE(SUM(monto),0) s FROM donations WHERE fecha>=?", (first,)).fetchone()["s"] or 0
        adp = cur.execute(
            """
            SELECT SUM(CASE WHEN estado='ADOPTADO' THEN 1 ELSE 0 END) a,
                   SUM(CASE WHEN estado='EN_PROCESO' THEN 1 ELSE 0 END) p
            FROM adoptions
        """
        ).fetchone()
        conn.close()
        return total_anim, total_pads, don_mes, (adp["a"] or 0), (adp["p"] or 0)

    def _pending(self, days=30):
        """Solo devuelve próximos entre hoy y hoy+days. NO incluye vencidos."""
        today = date.today()
        limit = today + timedelta(days=days)
        conn = get_conn()
        cur = conn.cursor()
        rows = []
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
                    # ignora fechas mal formateadas
                    pass
        conn.close()
        rows.sort(key=lambda x: x[2])
        return rows

    def _series_donaciones_6m(self):
        conn = get_conn()
        cur = conn.cursor()
        today = date.today().replace(day=1)
        labels, vals = [], []
        for i in range(5, -1, -1):
            m = (today - timedelta(days=30 * i)).replace(day=1)
            m2 = (today - timedelta(days=30 * (i - 1))).replace(day=1) if i > 0 else (today + timedelta(days=31))
            lab = f"{m.year}-{str(m.month).zfill(2)}"
            s = (
                cur.execute(
                    "SELECT COALESCE(SUM(monto),0) s FROM donations WHERE fecha>=? AND fecha<?",
                    (m.isoformat(), m2.isoformat()),
                ).fetchone()["s"]
                or 0
            )
            labels.append(lab)
            vals.append(float(s))
        conn.close()
        return labels, vals

    def _serie_animales_tipo(self):
        conn = get_conn()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT t.nombre as tipo, COUNT(*) c
            FROM animals a JOIN animal_types t ON t.id=a.especie_id
            GROUP BY t.nombre ORDER BY c DESC
        """
        ).fetchall()
        conn.close()
        labels = [r["tipo"] for r in rows]
        vals = [r["c"] for r in rows]
        return labels, vals

    # ---------- Render ----------
    def refresh(self):
        # KPIs
        ta, tp, dm, ad, pr = self._kpis()
        self.kpi_values[0].config(text=f"{ta:,}".replace(",", "."))
        self.kpi_values[1].config(text=f"{tp:,}".replace(",", "."))
        self.kpi_values[2].config(text=f"{dm:,.0f}".replace(",", "."))
        self.kpi_values[3].config(text=f"{ad:,}".replace(",", "."))
        self.kpi_cards[0][1].config(text="Animales registrados")
        self.kpi_cards[1][1].config(text="Padrinos activos")
        self.kpi_cards[2][1].config(text=f"Mes: {date.today():%Y-%m}")
        self.kpi_cards[3][1].config(text=f"{ad} adoptados / {pr} en proceso")

        # Pendientes (solo próximos; sin vencidos)
        self.tv_pending.delete(*self.tv_pending.get_children())
        today = date.today()
        for t, animal, d in self._pending(30):
            delta = (d - today).days
            tag = "soon" if delta <= 7 else "ok"
            self.tv_pending.insert("", "end", values=(t, animal, d.isoformat(), delta), tags=(tag,))
        # colores
        self.tv_pending.tag_configure("soon", background="#FEF3C7")
        self.tv_pending.tag_configure("ok", background="#F2F6FB")
        paint_rows(self.tv_pending)

        # Gráficos
        if MATPLOTLIB_OK:
            # Donaciones (línea con puntos)
            l, v = self._series_donaciones_6m()
            self.ax1.clear()
            self.ax1.plot(l, v, marker="o")
            self.ax1.set_title("Donaciones últimos 6 meses", fontsize=12)
            self.ax1.tick_params(axis="x", rotation=25, labelsize=8)
            self.ax1.tick_params(axis="y", labelsize=8)
            self.ax1.yaxis.set_major_locator(MaxNLocator(nbins=4))
            self.ax1.grid(axis="y", alpha=0.2)

            # Animales por tipo (barras horizontales)
            l2, v2 = self._serie_animales_tipo()
            self.ax2.clear()
            if v2:
                self.ax2.barh(l2[::-1], v2[::-1])
                self.ax2.set_xlabel("Cantidad", fontsize=10)
            self.ax2.set_title("Animales por tipo", fontsize=12)
            self.ax2.tick_params(axis="x", labelsize=9)
            self.ax2.tick_params(axis="y", labelsize=9)
            self.ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
            self.ax2.grid(axis="x", alpha=0.2)

            # espacio entre subplots ya está, reforzamos
            self.fig.subplots_adjust(hspace=0.4)
            self.canvas.draw()
