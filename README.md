# 🐾 AlbergueApp (Tkinter)

**AlbergueApp** es una aplicación de escritorio desarrollada en **Python** con **Tkinter** y **ttkbootstrap**, diseñada para gestionar de forma integral la información de un **albergue de animales**.
Permite administrar animales, donaciones, vacunas, desparasitaciones y adopciones, además de generar reportes automáticos en **CSV**, **Excel** y **PDF**.

---

## 🚀 Características principales

### 🐶 Animales
- Registro completo de animales con nombre, especie, sexo (`Macho / Hembra / ND`), edad y fecha de ingreso.
- Administración de tipos de animal (especies).
- Integración con los módulos de vacunas, desparasitaciones, adopciones y donaciones.

### 💖 Donaciones
- Asociación con **padrinos (sponsors)**, mostrando el **nombre** en lugar del ID.
- Registro de monto, método de pago y notas.
- Listado de donaciones por padrino o por animal.

### 💉 Vacunas y 🪱 Desparasitaciones
- Registro de vacuna o producto aplicado, fecha y próxima dosis.
- **Alertas automáticas** para aplicaciones próximas dentro de los próximos **7 días**.

### 🏡 Adopciones
- Estados: **EN_PROCESO**, **ADOPTADO**, **RECHAZADO**.
- Registro completo del adoptante (nombre, documento, teléfono, correo, dirección).
- Fecha de egreso y observaciones.

### 📊 Reportes
- Exportación a **CSV/Excel**.
- Generación de **PDF** con plantillas HTML mediante **xhtml2pdf** (opcionalmente **WeasyPrint**).
- Plantillas base en `reports/templates/`.

---

## 📁 Estructura del proyecto

```plaintext
AlbergueApp/
│
├── app.py                    # Ventana principal
├── db.py                     # Conexión SQLite + funciones CRUD
├── albergue.db               # Base de datos local
│
├── ui/
│   ├── animals.py            # Gestión de animales
│   ├── sponsors.py           # Gestión de padrinos/donantes
│   ├── donations.py          # Gestión de donaciones
│   ├── health.py             # Vacunas y desparasitaciones
│   ├── adoptions.py          # Gestión de adopciones
│   └── reports.py            # Reportes y exportaciones
│
├── reports/
│   └── templates/
│       ├── base.html
│       ├── animals_report.html
│       └── donations_report.html
│
├── assets/
│   └── logo.png              # Logo o ícono del albergue
│
├── requirements.txt
└── README.md
